from __future__ import (absolute_import, division, print_function,unicode_literals)
import os
import sys
from copy import deepcopy

import traceback
import pytz
import datetime
import time
import pendulum
import pandas as pd
import numpy as np
import uuid
from datetime import timedelta

import backtrader as bt
import alpaca_backtrader_api
import pandas_market_calendars as mcal

import logging
logging.basicConfig(format='_time=%(asctime)s | %(message)s', level=logging.INFO)

print_backup=deepcopy(print)
def print(message, *args):
    ts = pendulum.now('UTC').to_iso8601_string()
    print_backup("_time=" + ts,message,sep=' | ', *args,flush=True)

#======global settings
LOGGING = True
IS_LIVE=eval(os.environ["IS_LIVE"])
IS_BACKTEST = True if sys.argv[1] == "backtest" else False
SLIPPAGE = 0.001
BACKTEST_CASH = 10000
CHEAT_ON_CLOSE = True if IS_BACKTEST else False
SHORT_CASH =  True
TIMEFRAME = bt.TimeFrame.Minutes
COMPRESSION = 1
FROMDATE = pendulum.datetime( 2021, 2, 1,5,0,0, tz='UTC').in_timezone('America/New_York')  
TODATE =   pendulum.datetime( 2021, 2, 4,16,00,0, tz='UTC').in_timezone('America/New_York') 
EXPIRATION_BARS = 3
STOP_BARS = 30
SIGNAL_RSI_LONG = 40
SIGNAL_RSI_SHORT = 60
STOP_LOSS_PERC = 0.0015
SESSION_START_DELAY_HOURS = 0


#======universe
SYMBOLS = ['TSLA'] #NYSE
ca=mcal.get_calendar('NASDAQ')
schedule = ca.schedule(start_date=str(FROMDATE.date()), end_date=str(TODATE.date())).index.astype(str).to_list()

# ================= Sizer
class custom_Sizer(bt.Sizer):
    # 1/n portfolio sizing
    
    def __init__(self):
        pass

    def _getsizing(self, comminfo, cash, data, isbuy):
        
        size_per_asset = {S:(1/len(SYMBOLS) * 0.98) for S in SYMBOLS}   ### equal sizes for assets with buffer
        
        pos = self.broker.getposition(data).size
        
        if pos != 0:
            return pos
        else:
            cash = self.strategy.cashtotrade
            
            # long position
            if isbuy == True: 
                size = np.floor((cash * size_per_asset[data._name]) / data.close[0] )
                
            # short position
            else:
                size = np.floor((cash * size_per_asset[data._name]) / data.close[0] ) 
                size = -size
                
            self.strategy.log('event=sizer',f'asset={data._name}',f'cash={str(cash)}',f'size={str(size)}',f'isbuy={str(isbuy)}')
        return size


class StrategyStoploss(bt.Strategy):
    
    params = dict( )
    
    def __init__(self):
        self.live_bars = False
        self.o = { S:[None,None,None] for S in SYMBOLS }
        self.position_bars_none = {S:0 for S in SYMBOLS}
        self.position_bars_active = {S:0 for S in SYMBOLS}
        self.count_bars = 0
        self.new_bar = False
        self.last_bar = 0 
        self.whichord = ['main','stop','close']
        self.cashtotrade = 0
        self.session_running = False
        self.session_date = ''
        self.signal_rsi0 = SIGNAL_RSI_LONG
        
    def log(self,txt,*args):
        if LOGGING:                       # can be deactivated for wrapper optimizer 
            dt = self.data.datetime[0]
            dt = bt.num2date(dt)
            if IS_BACKTEST: print("_dt=" + dt.isoformat(),f"portfolio={'%.0f' % self.broker.getvalue()}", txt, *args) # only print portfolio value in BACKTEST, otherwise API call limit reached
            else: print("_dt=" + dt.isoformat(), txt, *args)
        
    def start(self):
        print("==================================================")
        print("event=logging",f"value={str(LOGGING)}")
        print("==================================================")
        

    def stop(self):
        print('==================================================')
        print("event=start",f"cash={str(self.broker.startingcash)}")
        print("event=end",f"cash={str(self.broker.getvalue())}")
        print('==================================================')
        sys.exit("Finished")
        
    def notify_store(self, msg, *args, **kwargs):
        super().notify_store(msg, *args, **kwargs)
        self.log(msg)
    
    def notify_fund(self, cash, value, fundvalue, shares):
        super().notify_fund(cash, value, fundvalue, shares)
    
    def notify_data(self, data, status, *args, **kwargs):
        super().notify_data(data, status, *args, **kwargs)
        print("event=notify_data",f"name={data._name}",f"status={data._getstatusname(status)}", *args)
        if data._getstatusname(status) == "LIVE":
            self.live_bars = True
    
    def oid(self):
        return str(uuid.uuid1()).replace('-','_')
            
    def notify_order(self, order):
        
        #infos 
        status = order.getstatusname()
        if status in ['Submitted']: return
        
        asset = order.data._name
        otype = order.getordername()
        buy='buy' if order.isbuy() else ''; sell='sell' if order.issell() else ''
        side=buy+sell
        
        # logging the order
        self.log("event=order",f"asset={asset}",f"label={order.info.label}",f"type={otype}",f"side={side}",f"price={'%.2f' % order.executed.price}",f"size={str(int(order.executed.size))}",f"margin={str(order.executed.margin)}",f"status={str(status)}",f"ref={str(order.ref)}")

        # print orderlist
        if status in ['Accepted','Completed']: self.print_orderlist(asset)
         
        # on completed Market order, create Stop order
        if status == 'Completed' and otype == 'Market':
            if order.info.label == 'main':
                # set stop order after main order completed!
                if self.o[asset][1] is None and self.o[asset][2] is None:
                    datas = {d._name:d for i, d in enumerate(self.datas) }
                    stop_price = np.round(order.executed.price * order.info.stop_loss_perc  ,2)
                    oid = self.oid()
                    if side=='buy':
                        stop  = self.sell(data=datas[asset],price=stop_price, size=order.executed.size, exectype=bt.Order.Stop,client_order_id=oid) # parent not working in live
                    else:
                        stop  = self.buy(data=datas[asset],price=stop_price, size=abs(order.executed.size), exectype=bt.Order.Stop,client_order_id=oid) # parent not working in live   
                    stop.addinfo(client_order_id=oid,label='stop')
                    self.o[asset][1] = stop
            return

        
        # NOT WORKING IN LIVE MODE
        # if stop-order is canceled successfully, close main position
        if status == 'Canceled' and otype == 'Stop':
            datas = {d._name:d for i, d in enumerate(self.datas) }
            self.log("event=close_main_expiration",f"asset={asset}")
            self.o[asset][2] = self.close(datas[asset],time_in_force='fok').addinfo(label='expiration')
        

    def notify_trade(self, trade):
        # new trade, not update of position!
        
        ttype='long' if trade.long==True else 'short'
        asset = trade.getdataname(); price = trade.price ; size = trade.size; status = trade.status; isclosed = trade.isclosed;
        side = 'buy' if size > 0 else 'sell'
        if size == 0: side = 'unclear'
        
        # log
        self.log("event=trade",f"asset={asset}",f"type={ttype}",f"price={'%.2f' % price}",f"size={str(size)}",f"commission={str(trade.commission)}",f"tradeid={str(trade.tradeid)}",f"ref={str(trade.ref)}",f"status={str(status)}",f"isclosed={str(isclosed)}")  
    
    def print_orderlist(self,SYMB):
        orders = [e.getstatusname() if not e is None else '' for e in self.o[SYMB]]
        self.log("event=orderlist",f"asset={SYMB}",f"value={str(orders)}")
                
    def cancel_orders(self,SYMB,client_order_id=None):
        self.log("event=cancel_orders",f"asset={SYMB}",f"client_order_id={str(client_order_id)}")
        # backtrader part
        if client_order_id is None:
            for o in self.o[SYMB]: 
                if not o is None: self.broker.cancel(o)
        else:
            orders=[o for o in self.o[SYMB] if o.client_order_id == client_order_id ]
            if len(orders) > 0:
                for o in orders:
                    self.broker.cancel(o)
        
    def validate_session(self):
        #===== date
        now_time = bt.num2date(self.data.datetime[0])  # not tzinfo, in UTC
        now_date = str(now_time.date())
        if self.session_date != now_date:  # new day
            # skip day in backtest
            if IS_BACKTEST:
                if not now_date in schedule: return False
            dm = ca.schedule(start_date=now_date, end_date=now_date)
            if dm.shape[0] == 0: return False                               # no market today
            self.market_open = dm.market_open[0].to_pydatetime().replace(tzinfo=None)     # not tzinfo, in UTC
            if SESSION_START_DELAY_HOURS > 0 : self.market_open = pendulum.parse(str(self.market_open)).add(hours=SESSION_START_DELAY_HOURS).replace(tzinfo=None) 
            self.market_close = dm.market_close[0].to_pydatetime().replace(tzinfo=None)  # not tzinfo, in UTC
            self.log("event=marketinfo",f"market_open={self.market_open}",f"market_close={self.market_close}")
            self.session_date = now_date
            self.count_bars == 0
        
        #====== session
        if float( (now_time - self.market_open ).total_seconds() / 60) >= 1:  # start trading
            self.session_running = True
            
        # stop trading
        if self.session_running:
            if float((now_time - self.market_close ).total_seconds() / 60) >= -10:
                self.log('event=session_finished','mesage=zzzzzzzzzzzzzzzzzzzzzzzzz')
                self.session_running = False
        
        if not self.session_running: return False
        
        return True

    
    def next(self):
        
        #=========== Return 0 if no live bars
        if not self.live_bars and not IS_BACKTEST:
            # only run code if we have live bars (today's bars).
            # ignore if we are backtesting
            return
        
        #===========  has any asset reached a new bar?
        self.new_bar = False
        for i, d in enumerate(self.datas): 
            if d.datetime[0] > self.last_bar: 
                self.new_bar = True
                self.last_bar = d.datetime[0]
                self.count_bars += 1
                self.log('event=new_bar','mesage=____________________________________________________')
                break
        if not self.new_bar: return
        
        #=========== trading calender and session
        if not self.validate_session(): return
        
        #=========== Record current positions
        POS = {d._name:self.getposition(d).size for i, d in enumerate(self.datas) }
        self.log("event=positions","value=|" + str(POS) + "|")
        
        #=========== recalculate cash for trading, when out of market
        if all(x== 0 for x in POS.values() ):
            
            self.cashtotrade = float(self.broker.cash)
            self.log("event=cash",'message=adjust_cash_available_for_trade',f'value={str(self.cashtotrade)}')

             #============ check stop
            if self.count_bars >= STOP_BARS:
                self.log("event=stop",f"message=STOP_BARS_reached")
                self.cerebro.runstop()
        
        
        for i, d in enumerate(self.datas): 
            
            #========= d is data object of asset
            SYMB=d._name 

            #========== data
            p_open_bar = p_open_tick = d.open[0]
            p_close_bar = p_close_tick = d.close[0]
            p_volume_bar = p_volume_tick = d.volume[0]

            # ========= logging info
            self.log("event=bar",f"asset={SYMB}",f"open={str(p_open_bar)}",f"close={str(p_close_bar)}",f"count={str(self.count_bars)}") #  '%.2f' % p_last_buy

            # ========= log orderlist
            self.print_orderlist(SYMB)
            
            ####################### TRADING LOGIC #####################
            
            #======== position size
            position = self.getposition(d) 
            position_size = position.size
            position_price = position.price
            POS[SYMB] = position_size

            #========expiration window and bar count
            if position_size == 0: 
                self.position_bars_active[SYMB] = 0
                self.position_bars_none[SYMB] += 1    
            else: 
                self.position_bars_active[SYMB] += 1
                self.position_bars_none[SYMB] = 0
  
            #=======orderlist cleaning
            if position_size == 0:
                o = self.o[SYMB][0]  # main order
                if not o is None:
                    # case: main order not filled after 2 bars
                    if self.position_bars_none[SYMB] >= 2 and o.status == o.Accepted :
                        self.log("event=orders_cleaned_mainorder_notfilled",f"asset={SYMB}",f"ref={str(o.ref)}")
                        self.cancel_orders(SYMB)
                        self.o[SYMB] = [None,None,None]
                        continue
                    # case: cycle completed [Completed, *, *] | position = 0 --> reset all
                    if o.status in [o.Completed, o.Canceled, o.Expired]:
                        self.o[SYMB] = [None,None,None]
                        self.log("event=orders_cleaned_completed_cycle",f"asset={SYMB}",f"message=----------")
                        continue

                    # case main order was rejected
                    if o.status in [o.Rejected]:
                        self.o[SYMB] = [None,None,None]
                        self.log("event=orders_cleaned_mainorder_rejected",f"asset={SYMB}",f"message=----------")
                        continue

                # case stop order was rejected
            
            #========= switch dummy signals
            if position_size < 0: self.signal_rsi0 = SIGNAL_RSI_LONG
            if position_size > 0: self.signal_rsi0  = SIGNAL_RSI_SHORT
            signal_rsi0 = self.signal_rsi0
            signals = dict(
                signal_rsi0 = signal_rsi0,
                bars_active =  self.position_bars_active[SYMB] ,
                bars_none = self.position_bars_none[SYMB] 
            )

            self.log("event=signal",f"asset={SYMB}",f"value=|{str(signals)}|")
            
            # ======== in the market: expiration:
            
            if position_size != 0 and self.position_bars_active[SYMB] >= 1:

                #=============window expired?
                if self.position_bars_active[SYMB] >= EXPIRATION_BARS :
                    self.log("event=position_expired",f"asset={SYMB},value=|--------------------EXPIRED--------------------|")
                    o = self.o[SYMB][1] # stop order
                    # case stop order was removed or doesnt exist
                    if o is None:
                        self.log("event=close_position",f"asset={SYMB}")
                        self.o[SYMB][2] = self.close(d,time_in_force='fok').addinfo(label='expiration')
                        continue
                    # cancel stop order
                    if o.status != o.Canceled:
                        #self.log("event=cancel_stop",f"asset={SYMB}")
                        #if not IS_BACKTEST: self.cancel_orders(SYMB,client_order_id=o.info.client_order_id)  # hack in case no nofity_order ("Canceled") is sent:
                        #self.broker.cancel(o)
                        #self.log("event=close_position",f"asset={SYMB}")
                        #self.o[SYMB][2] = self.close(d,time_in_force='fok').addinfo(label='expiration')
                        continue

            if  position_size == 0 and self.position_bars_none[SYMB] >= 2 and self.count_bars < STOP_BARS:
                
                # ======= signal long position
                if (  signal_rsi0 <= SIGNAL_RSI_LONG  and all(x is None for x in self.o[SYMB])  ) : 

                    self.log("event=position_open",f"asset={SYMB}","position_type=long","value=|--------------------LONG--------------------|")
                    stop_loss_perc = 1 - STOP_LOSS_PERC
                    oid = self.oid()
                    mainside = self.buy(data=d,exectype=bt.Order.Market, transmit=True,time_in_force='fok',client_order_id=oid) # transmit false fails
                    mainside.addinfo(label='main',stop_loss_perc=stop_loss_perc,client_order_id=oid)
                    self.o[SYMB] = [mainside,None,None]

                    continue 


                # ======= signal short position
                if ( signal_rsi0 >= SIGNAL_RSI_SHORT and all(x is None for x in self.o[SYMB])  ) : 

                    self.log("event=position_open",f"asset={SYMB}","position_type=short","value=|--------------------SHORT--------------------|")
                    stop_loss_perc = 1 + STOP_LOSS_PERC
                    oid = self.oid()
                    mainside = self.sell(data=d,exectype=bt.Order.Market, transmit=True,time_in_force='fok',client_order_id=oid) # transmit false fails
                    mainside.addinfo(label='main',stop_loss_perc=stop_loss_perc,client_order_id=oid)
                    self.o[SYMB] = [mainside,None,None]
                    continue
            

def setup_cerebro(IS_BACKTEST):
    #=============Setup Cerebro
    cerebro = bt.Cerebro(stdstats=False,tradehistory=True)

    # risk and tracking
    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.Trades)
    cerebro.addobserver(bt.observers.DrawDown)

    # strategy
    cerebro.addstrategy(StrategyStoploss)

    # Add sizer
    cerebro.addsizer(custom_Sizer)

    # data store
    store = alpaca_backtrader_api.AlpacaStore(
        paper=not IS_LIVE,
        usePolygon=False
    )


    #===========configuring broker
    if IS_BACKTEST:
        cerebro.broker.set_slippage_perc(SLIPPAGE,slip_open=True,slip_limit=True,slip_match=True,slip_out=False)
        cerebro.broker.set_coc(CHEAT_ON_CLOSE)
        cerebro.broker.setcash(BACKTEST_CASH)
        cerebro.broker.set_shortcash(SHORT_CASH)
        
    else:    
        broker = store.getbroker()
        cerebro.setbroker(broker)

    #===========configuring data
    DataFactory = store.getdata  # or use alpaca_backtrader_api.AlpacaData 
    # in backtest, data is minute-bar data
    # in live, tickdata is fed via websocket! next() is called by tick, so data need to be resampled to higher resolution!
    D={}
    for SYMB in SYMBOLS:
        if IS_BACKTEST:
            D[SYMB] = DataFactory(dataname=SYMB,historical=True,fromdate=FROMDATE,todate=TODATE,timeframe=TIMEFRAME,compression=COMPRESSION,qcheck=0.00) 
        else:
            fromdate = pendulum.now('US/Eastern') - timedelta( minutes=70)
            D[SYMB] = DataFactory(dataname=SYMB,historical=False,fromdate=fromdate,timeframe=bt.TimeFrame.Ticks,compression=COMPRESSION,backfill_start=True,backfill=True,qcheck=0.5 )
            cerebro.adddata(D[SYMB],name=SYMB) # tickdata in live mode
        cerebro.resampledata(D[SYMB],name=SYMB,timeframe=TIMEFRAME,compression=COMPRESSION)# bardata in live mode


    # analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.broker.BACKTEST = []
    return cerebro


# ================ run backtest
cerebro = setup_cerebro(IS_BACKTEST)
results=cerebro.run() 


