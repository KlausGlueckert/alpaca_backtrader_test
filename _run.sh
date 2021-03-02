source ENV.sh

docker stop alpaca_backtrader_test_test1
docker rm alpaca_backtrader_test_test1

docker-compose -f docker-compose.yml up --force-recreate -d
docker logs alpaca_backtrader_test_test1 --follow

# for dev:
# docker exec -it alpaca_backtrader_test python /app/main.py