echo "############################| IS_LIVE=${IS_LIVE}"
echo "############################| IS_BACKTEST=True..."
python strat_stoploss.py backtest 2>&1 | tee test_stoploss.log ; 
python strat_longshort.py backtest 2>&1 | tee test_longshort.log ; 
python -m pytest -v -s test_stoploss.py --log test_stoploss.log 2>&1 | tee -a test_stoploss.log ; 
python -m pytest -v -s test_longshort.py --log test_longshort.log 2>&1 | tee -a test_longshort.log ; 


echo "############################| IS_LIVE=${IS_LIVE}"
echo "############################| IS_BACKTEST=False..."
#python strat_stoploss.py real 2>&1 | tee notifymessages_paperlive.log ; 
#python -m pytest -v -s test_notifymessages.py --log notifymessages_paperlive.log 2>&1  | tee -a notifymessages_paperlive.log ; 