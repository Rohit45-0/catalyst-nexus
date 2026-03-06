@echo off
echo Starting Catalyst Nexus ARQ Worker...
echo Make sure Redis is running!
echo.
set PYTHONPATH=%cd%
python -m arq backend.app.worker.WorkerSettings
