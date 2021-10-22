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
   * ```EXPIRATION_BARS``` number of 1-min bars after which position is closed automatically (expired)
   * ```STOP_BARS```       number of 1-min bars after which the test is completed
   * ```STOP_LOSS_PERC```  the stoploss level after main order

# Results

### running from out-of-market state
i made the following observations
* soemtimes (not always), no notify_order messages are sent when stoploss order is canceled or completed (order status is updated though on the object)...this makes it not possible to trigger orders from the notify_order function
* there are duplicated notify_order messages, not allowing a programmer to place trading logic in the ```notify_order``` function)

### relaunch from in-market-state with pending stop-orders
currently not possible, the stop-order was stored during last runtime in the order object. it is better to cancel all pending orders upon relaunch

### relaunch from in-market-state with no pending orders
TBD