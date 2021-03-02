echo "############################| IS_LIVE=${IS_LIVE}"
echo "############################| IS_BACKTEST=True..."
python stoploss.py backtest 2>&1 | tee notifymessages_backtest.log ; 
python -m pytest -v -s test_notifymessages.py --log notifymessages_backtest.log 2>&1 | tee -a notifymessages_backtest.log ; 

echo "############################| IS_LIVE=${IS_LIVE}"
echo "############################| IS_BACKTEST=False..."
python stoploss.py real 2>&1 | tee notifymessages_paperlive.log ; 
python -m pytest -v -s test_notifymessages.py --log notifymessages_paperlive.log 2>&1  | tee -a notifymessages_paperlive.log ; 