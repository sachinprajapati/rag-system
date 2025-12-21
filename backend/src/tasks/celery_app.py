from celery import Celery
import os

def make_celery(app):
    celery = Celery(app.import_name, broker=os.getenv('REDIS_URL'))
    celery.conf.update(app.config)
    return celery

celery_app = make_celery(app)