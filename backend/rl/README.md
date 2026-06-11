RL Trainer
===========

This worker runs continuously to keep RL policies and ML predictors up-to-date.

Environment variables
- `TRAIN_INTERVAL_SECONDS` — seconds between training cycles (default: `21600` / 6 hours)
- `RL_EPISODES` — number of episodes for RL training (default: `60`)
- `RL_SYMBOLS` — comma-separated symbol list to train (default: uses `DEFAULT_RL_SYMBOLS`)
- `FORCE_RETRAIN` — `true`/`false`, force retrain even if agent exists (default: `false`)
- `TRAIN_ONCE` — `true`/`false`, run a single cycle and exit (default: `false`)
- `TRAINER_LOG_LEVEL` — logger level (default: `INFO`)

Docker Compose
- The `trainer` service is added to `docker-compose.yml`. To run only the trainer locally:

```bash
docker compose up -d trainer
docker logs -f nexusai-trainer
```

Notes
- Trainer persists RL agent files to the `rl_agents` Docker volume mounted at `/app/rl/saved_agents`.
- The worker calls `train_rl_batch` to train tabular RL policies and uses `app.ml.predictor.StockPredictor` to retrain ML models.
