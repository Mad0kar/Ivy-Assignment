#!/bin/bash
# usage: ./api.sh "/v1/listings?limit=1"
set -a; source /Users/devanshsinghal/ivy-homes-assignment/.env; set +a
curl -s -H "X-API-Key: $IVY_API_KEY" "$IVY_BASE_URL$1"
