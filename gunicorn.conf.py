"""Gunicorn settings for the hosted server (read automatically from the working directory).

The free Render plan has 512 MB. One worker peaks at about 320 MB on a large upload; the live server
was found running two workers (2026-11-20, WEB_CONCURRENCY or a dashboard start command overriding
render.yaml), and a second upload then ran the container out of memory. One worker with threads
queues uploads through services/heavy_lock.py instead.
"""
workers = 1
threads = 4
timeout = 120


def on_starting(server):
    # Applies even when the start command or WEB_CONCURRENCY asks for more workers.
    server.num_workers = 1
