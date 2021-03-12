# alpaca-backtrader unit tests

* https://github.com/alpacahq/alpaca-backtrader-api
* https://github.com/backtrader

### objective

* verify that the alpaca-backtrader framework works reliably in paper/live trading and behaves exactly as in backtest mode
* this test aims to replicate a real trading scneario, where the programmer wants full controll of the order flow of main-orders and stop-orders
    * stop-orders have to be cancelled before positions are closed, otherwise Alpaca will rejected the closing order
    * only after a mainorder is 100% filled, the stop-order should be created  - this is achieved by creating the stop-loss order in the "notify_order" function, when the mainside market order is "Completed"
* while backtrader operates with parents-child orders to connect a main-order to a stop-order  (with transmit=False) this functionality is not replicated by the alpaca-backtrader framework - therefore this test aims to simulate manual handling of main-orders and stop-orders and evaluate if it behaves according to the backtest

### structure of the test

* the backtrader strategy ```stoploss.py``` is run first in backtest mode and then again in paper/live mode to replicate the behavior
* a log is written to *.backtest.log and *.paperlive.log
* the log is then parsed and the events evaluated according to expected behaviors
* for example, before a position is closed, the stop-loss order has to be cancelled first, which has to result in 2 notify_order events (cancel the stop-order, completed sell event)

### backtrader test stragey

* the strategy opens a long position and upon completion a stop-loss order to cover the downside
* either a stop-loss occurs within 2 bars or after 2 bars the position is closed with an "expiration" close order
* following, a short position is open, again with a stop-loss order to protect from rising prices
* again, either a stop-loss occurs within 2 bars or after 2 bars the position is closed with an "expiration" close order
* this cycle is repeated, until ```EXPIRATION_BARS``` is reached

### what is being tested

* do notify_order messages work as expected for Market and Stop-Market orders (Accepted, Completed, Canceled)?
* does notify_order event occur after Stop/Market order is canceled by the strategy?
* does notify_order event occur after Stop order is triggered by Alpaca?
* are there duplicate event messages or exactly one message per event as expected? (this is crucial, otherwise one cannot place trading logic in the ```notify_order``` function)
* review test_notifymessages.py fo details

### install / pre-requisites

* docker-compose
```
sudo curl -L "https://github.com/docker/compose/releases/download/1.25.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose;
sudo chmod +x /usr/local/bin/docker-compose;
```

* docker
```
sudo apt update ; 
sudo apt install apt-transport-https ca-certificates curl software-properties-common;
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -;
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable";
sudo apt update;
sudo apt-cache policy docker-ce;
sudo apt install docker-ce -y;
sudo systemctl status docker;
```

### how to run

* clone the repo: ```git clone ```
* enter API keys in ```ENV.sh```
* ```bash _run.sh```

### what can be customized

* customize the ```Dockerfile``` or create your own to test different package / python versions
* specify the Dockerfile to test in ```docker-compose.yml```
* in ```stoploss.py```
   * ```EXPIRATION_BARS``` # number of 1-min bars after which position is closed automatically (expired)
   * ```STOP_BARS```       # number of 1-min bars after which the test is completed
   * ```STOP_LOSS_PERC```  # the stoploss level after main order

# Results

### running from out-of-market state

* no notify_order message when stoploss order is accepted (order status is updated though)
* no notify_order messages when a stoploss order is completed, when using self.broker.cancel(order) (order status is updated though)
* no notify_order messages when a stoploss order is canceled, when using self.broker.cancel(order)  (order status is updated though)
* there are duplicated notify_order messages, not allowing a programmer to place trading logic in the ```notify_order``` function)
* sometimes the first main order is just "Rejected" 1-2x until it is placed, it could be because of the "fok" setting, this must be investigated more

### relaunch from in-market-state with pending stop-orders
currently not possible, the stop-order was stored during last runtime in the order object. it is better to cancel all pending orders upon relaunch

### relaunch from in-market-state with no pending orders
assume our app crashes and we need to resume the strategy. We would expect that the engine resumes with the current broker state (open position). Unfortunately, some very weired behavior occurs. from this observations it seems, the engine does not reliably and quickly pick up the current broker state. Current conclusion is that resuming must be done by first cancelling all positions and orders and then waiting for new signals.

* (v) it correctly sets the position to open
* (v) when running into expiration it correctly tries to close the position
* (x) closing the position only works after 2 attempts, before it throws an error, claiming 0 qty is available if in fact, before it has recognized the open position correctly

```
error submitting order code: 40310000. msg: insufficient qty available for order (requested: 144, available: 0)
```


```
============================= test session starts ==============================
platform linux -- Python 3.6.12, pytest-6.2.2, py-1.10.0, pluggy-0.13.1 -- /usr/local/bin/python
cachedir: .pytest_cache
rootdir: /app
collecting ... Start Evaluation Unit Tests................................................................
-----------------LOG notifymessages_backtest.log
log=notifymessages_backtest.log starting checks....................
logfile opened notifymessages_backtest.log with cols:
Index(['', 'event', 'value', 'name', 'status', '_dt', 'portfolio', 'mesage',
       'market_open', 'market_close', 'message', 'asset', 'open', 'close',
       'count', 'position_type', 'cash', 'size', 'isbuy', 'label', 'type',
       'side', 'price', 'margin', 'ref', 'commission', 'tradeid', 'isclosed'],
      dtype='object')
collected 6 items

test_notifymessages.py::test_check1__has_expired_bars PASSED
test_notifymessages.py::test_check2__has_stopporders_completed PASSED
test_notifymessages.py::test_check3__positions_must_be_equal_mainorders PASSED
test_notifymessages.py::test_check4__canceledstops_must_be_euqal_canceledstoporders PASSED
test_notifymessages.py::test_check5__expiredpositions_must_be_equal_completedexpiredorders PASSED
test_notifymessages.py::test_check6__no_rejected_orders PASSED

============================== 6 passed in 0.32s ===============================
############################| IS_LIVE=False
############################| IS_BACKTEST=False...
_time=2021-03-12 18:55:42,224 | connected to: wss://paper-api.alpaca.markets/stream
_time=2021-03-12T18:55:42.448754Z | ==================================================
_time=2021-03-12T18:55:42.453868Z | event=logging | value=True
_time=2021-03-12T18:55:42.453901Z | ==================================================
_time=2021-03-12T18:55:42.469297Z | event=notify_data | name=TSLA | status=DELAYED
_time=2021-03-12 18:55:43,026 | connected to: wss://data.alpaca.markets/stream
_time=2021-03-12T18:56:02.962981Z | _dt=2021-03-12T17:46:00 | event=trade | asset=TSLA | type=long | price=685.89 | size=144 | commission=0.0 | tradeid=0 | ref=1 | status=1 | isclosed=False
_time=2021-03-12T18:56:33.349323Z | event=notify_data | name=TSLA | status=LIVE
_time=2021-03-12T18:57:00.520847Z | _dt=2021-03-12T18:57:00 | event=new_bar | mesage=____________________________________________________
_time=2021-03-12T18:57:00.539743Z | _dt=2021-03-12T18:57:00 | event=marketinfo | market_open=2021-03-12 14:30:00 | market_close=2021-03-12 21:00:00
_time=2021-03-12T18:57:00.539837Z | _dt=2021-03-12T18:57:00 | event=positions | value=|{'TSLA': 144}|
_time=2021-03-12T18:57:00.539893Z | _dt=2021-03-12T18:57:00 | event=bar | asset=TSLA | open=686.3 | close=680.0 | count=1
_time=2021-03-12T18:57:00.540000Z | _dt=2021-03-12T18:57:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T18:57:00.540095Z | _dt=2021-03-12T18:57:00 | event=signal | asset=TSLA | value=|{'signal_rsi0': 60, 'bars_active': 1, 'bars_none': 0}|
_time=2021-03-12T18:58:00.444099Z | _dt=2021-03-12T18:58:00 | event=new_bar | mesage=____________________________________________________
_time=2021-03-12T18:58:00.449284Z | _dt=2021-03-12T18:58:00 | event=positions | value=|{'TSLA': 144}|
_time=2021-03-12T18:58:00.449350Z | _dt=2021-03-12T18:58:00 | event=bar | asset=TSLA | open=686.87 | close=680.0 | count=2
_time=2021-03-12T18:58:00.449406Z | _dt=2021-03-12T18:58:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T18:58:00.449449Z | _dt=2021-03-12T18:58:00 | event=signal | asset=TSLA | value=|{'signal_rsi0': 60, 'bars_active': 2, 'bars_none': 0}|
_time=2021-03-12T18:58:00.449485Z | _dt=2021-03-12T18:58:00 | event=position_expired | asset=TSLA,value=|--------------------EXPIRED--------------------|
_time=2021-03-12T18:58:00.449518Z | _dt=2021-03-12T18:58:00 | event=close_position | asset=TSLA
_time=2021-03-12T18:58:00.939401Z | _dt=2021-03-12T18:58:00 | error submitting order code: 40310000. msg: insufficient qty available for order (requested: 144, available: 0)
_time=2021-03-12T18:59:00.284251Z | _dt=2021-03-12T18:59:00 | event=order | asset=TSLA | label=expiration | type=Market | side=sell | price=0.00 | size=0 | margin=None | status=Rejected | ref=2
_time=2021-03-12T18:59:00.619954Z | _dt=2021-03-12T18:59:00 | event=new_bar | mesage=____________________________________________________
_time=2021-03-12T18:59:00.625135Z | _dt=2021-03-12T18:59:00 | event=positions | value=|{'TSLA': 144}|
_time=2021-03-12T18:59:00.625203Z | _dt=2021-03-12T18:59:00 | event=bar | asset=TSLA | open=680.0 | close=680.0 | count=3
_time=2021-03-12T18:59:00.625239Z | _dt=2021-03-12T18:59:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T18:59:00.625308Z | _dt=2021-03-12T18:59:00 | event=signal | asset=TSLA | value=|{'signal_rsi0': 60, 'bars_active': 3, 'bars_none': 0}|
_time=2021-03-12T18:59:00.625374Z | _dt=2021-03-12T18:59:00 | event=position_expired | asset=TSLA,value=|--------------------EXPIRED--------------------|
_time=2021-03-12T18:59:00.625415Z | _dt=2021-03-12T18:59:00 | event=close_position | asset=TSLA
_time=2021-03-12T18:59:01.545809Z | _dt=2021-03-12T18:59:00 | error submitting order code: 40310000. msg: insufficient qty available for order (requested: 144, available: 0)
_time=2021-03-12T19:00:00.068438Z | _dt=2021-03-12T19:00:00 | event=order | asset=TSLA | label=expiration | type=Market | side=sell | price=0.00 | size=0 | margin=None | status=Rejected | ref=3
_time=2021-03-12T19:00:00.377846Z | _dt=2021-03-12T19:00:00 | event=new_bar | mesage=____________________________________________________
_time=2021-03-12T19:00:00.383017Z | _dt=2021-03-12T19:00:00 | event=positions | value=|{'TSLA': 144}|
_time=2021-03-12T19:00:00.383087Z | _dt=2021-03-12T19:00:00 | event=bar | asset=TSLA | open=680.0 | close=684.58 | count=4
_time=2021-03-12T19:00:00.383126Z | _dt=2021-03-12T19:00:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:00:00.383217Z | _dt=2021-03-12T19:00:00 | event=signal | asset=TSLA | value=|{'signal_rsi0': 60, 'bars_active': 4, 'bars_none': 0}|
_time=2021-03-12T19:00:00.383253Z | _dt=2021-03-12T19:00:00 | event=position_expired | asset=TSLA,value=|--------------------EXPIRED--------------------|
_time=2021-03-12T19:00:00.383287Z | _dt=2021-03-12T19:00:00 | event=close_position | asset=TSLA
_time=2021-03-12T19:01:00.549703Z | _dt=2021-03-12T19:01:00 | event=order | asset=TSLA | label=expiration | type=Market | side=sell | price=0.00 | size=0 | margin=None | status=Accepted | ref=4
_time=2021-03-12T19:01:00.554843Z | _dt=2021-03-12T19:01:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:01:00.560002Z | _dt=2021-03-12T19:01:00 | event=order | asset=TSLA | label=expiration | type=Market | side=sell | price=0.00 | size=0 | margin=None | status=Accepted | ref=4
_time=2021-03-12T19:01:00.565117Z | _dt=2021-03-12T19:01:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:01:00.570247Z | _dt=2021-03-12T19:01:00 | event=order | asset=TSLA | label=expiration | type=Market | side=sell | price=0.00 | size=0 | margin=None | status=Accepted | ref=4
_time=2021-03-12T19:01:00.575361Z | _dt=2021-03-12T19:01:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:01:00.580487Z | _dt=2021-03-12T19:01:00 | event=order | asset=TSLA | label=expiration | type=Market | side=sell | price=684.63 | size=-144 | margin=0.0 | status=Completed | ref=4
_time=2021-03-12T19:01:00.585602Z | _dt=2021-03-12T19:01:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:01:00.590786Z | _dt=2021-03-12T19:01:00 | event=trade | asset=TSLA | type=long | price=685.89 | size=0.0 | commission=0.0 | tradeid=0 | ref=1 | status=2 | isclosed=True
_time=2021-03-12T19:01:00.878801Z | _dt=2021-03-12T19:01:00 | event=new_bar | mesage=____________________________________________________
_time=2021-03-12T19:01:00.878929Z | _dt=2021-03-12T19:01:00 | event=positions | value=|{'TSLA': -144}|
_time=2021-03-12T19:01:00.879012Z | _dt=2021-03-12T19:01:00 | event=bar | asset=TSLA | open=684.72 | close=685.7 | count=5
_time=2021-03-12T19:01:00.879112Z | _dt=2021-03-12T19:01:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:01:00.879172Z | _dt=2021-03-12T19:01:00 | event=signal | asset=TSLA | value=|{'signal_rsi0': 40, 'bars_active': 5, 'bars_none': 0}|
_time=2021-03-12T19:01:00.879206Z | _dt=2021-03-12T19:01:00 | event=position_expired | asset=TSLA,value=|--------------------EXPIRED--------------------|
_time=2021-03-12T19:01:00.879251Z | _dt=2021-03-12T19:01:00 | event=close_position | asset=TSLA
_time=2021-03-12T19:02:00.287163Z | _dt=2021-03-12T19:02:00 | event=order | asset=TSLA | label=expiration | type=Market | side=buy | price=0.00 | size=0 | margin=None | status=Accepted | ref=5
_time=2021-03-12T19:02:00.292324Z | _dt=2021-03-12T19:02:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:02:00.297470Z | _dt=2021-03-12T19:02:00 | event=order | asset=TSLA | label=expiration | type=Market | side=buy | price=0.00 | size=0 | margin=None | status=Accepted | ref=5
_time=2021-03-12T19:02:00.302639Z | _dt=2021-03-12T19:02:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:02:00.307776Z | _dt=2021-03-12T19:02:00 | event=order | asset=TSLA | label=expiration | type=Market | side=buy | price=0.00 | size=0 | margin=None | status=Accepted | ref=5
_time=2021-03-12T19:02:00.312922Z | _dt=2021-03-12T19:02:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:02:00.323290Z | _dt=2021-03-12T19:02:00 | event=order | asset=TSLA | label=expiration | type=Market | side=buy | price=685.87 | size=144 | margin=0.0 | status=Completed | ref=5
_time=2021-03-12T19:02:00.323341Z | _dt=2021-03-12T19:02:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:02:00.323428Z | _dt=2021-03-12T19:02:00 | event=trade | asset=TSLA | type=long | price=685.87 | size=144.0 | commission=0.0 | tradeid=0 | ref=1 | status=1 | isclosed=False
_time=2021-03-12T19:02:00.598973Z | _dt=2021-03-12T19:02:00 | event=new_bar | mesage=____________________________________________________
_time=2021-03-12T19:02:00.604133Z | _dt=2021-03-12T19:02:00 | event=positions | value=|{'TSLA': 0}|
_time=2021-03-12T19:02:00.609261Z | _dt=2021-03-12T19:02:00 | event=cash | message=adjust_cash_available_for_trade | value=99642.88
_time=2021-03-12T19:02:00.609324Z | _dt=2021-03-12T19:02:00 | event=bar | asset=TSLA | open=680.0 | close=680.0 | count=6
_time=2021-03-12T19:02:00.609378Z | _dt=2021-03-12T19:02:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:02:00.614521Z | _dt=2021-03-12T19:02:00 | event=signal | asset=TSLA | value=|{'signal_rsi0': 40, 'bars_active': 0, 'bars_none': 1}|
_time=2021-03-12T19:03:00.582120Z | _dt=2021-03-12T19:03:00 | event=new_bar | mesage=____________________________________________________
_time=2021-03-12T19:03:00.587299Z | _dt=2021-03-12T19:03:00 | event=positions | value=|{'TSLA': 0}|
_time=2021-03-12T19:03:00.592447Z | _dt=2021-03-12T19:03:00 | event=cash | message=adjust_cash_available_for_trade | value=99642.88
_time=2021-03-12T19:03:00.597586Z | _dt=2021-03-12T19:03:00 | event=bar | asset=TSLA | open=680.0 | close=680.0 | count=7
_time=2021-03-12T19:03:00.597645Z | _dt=2021-03-12T19:03:00 | event=orderlist | asset=TSLA | value=['', '', '']
_time=2021-03-12T19:03:00.597704Z | _dt=2021-03-12T19:03:00 | event=signal | asset=TSLA | value=|{'signal_rsi0': 40, 'bars_active': 0, 'bars_none': 2}|
_time=2021-03-12T19:03:00.597768Z | _dt=2021-03-12T19:03:00 | event=position_open | asset=TSLA | position_type=long | value=|--------------------LONG--------------------|
_time=2021-03-12T19:03:00.603110Z | _dt=2021-03-12T19:03:00 | event=sizer | asset=TSLA | cash=99642.88 | size=143.0 | isbuy=True
```

