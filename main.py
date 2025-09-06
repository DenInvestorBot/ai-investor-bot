==> Running 'python main.py'
INFO:ai-investor-bot:Использую токен из ENV 'BOT_TOKEN'
INFO:apscheduler.scheduler:Adding job tentatively -- it will be properly scheduled when the scheduler starts
ERROR:ai-investor-bot:Не удалось импортировать модуль ipo_monitor
Traceback (most recent call last):
  File "/opt/render/project/src/main.py", line 28, in _resolve_runner
    m = importlib.import_module(module_name)
  File "/opt/render/project/python/Python-3.10.13/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 883, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/opt/render/project/src/ipo_monitor.py", line 10, in <module>
    import httpx
ModuleNotFoundError: No module named 'httpx'
INFO:apscheduler.scheduler:Adding job tentatively -- it will be properly scheduled when the scheduler starts
ERROR:ai-investor-bot:Не удалось импортировать модуль reddit_monitor
Traceback (most recent call last):
  File "/opt/render/project/src/main.py", line 28, in _resolve_runner
    m = importlib.import_module(module_name)
  File "/opt/render/project/python/Python-3.10.13/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 883, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/opt/render/project/src/reddit_monitor.py", line 10, in <module>
    import httpx
ModuleNotFoundError: No module named 'httpx'
INFO:apscheduler.scheduler:Adding job tentatively -- it will be properly scheduled when the scheduler starts
INFO:apscheduler.scheduler:Adding job tentatively -- it will be properly scheduled when the scheduler starts
INFO:apscheduler.scheduler:Added job "run_crypto_monitor" to job store "default"
INFO:apscheduler.scheduler:Added job "_resolve_runner.<locals>._stub" to job store "default"
INFO:apscheduler.scheduler:Added job "_resolve_runner.<locals>._stub" to job store "default"
INFO:apscheduler.scheduler:Added job "main.<locals>.<lambda>" to job store "default"
INFO:apscheduler.scheduler:Scheduler started
INFO:ai-investor-bot:Bot starting polling…
INFO:apscheduler.scheduler:Scheduler started
