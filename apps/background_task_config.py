from background_task.apps import BackgroundTasksAppConfig


class BackgroundTaskConfig(BackgroundTasksAppConfig):
    default_auto_field = "django.db.models.AutoField"
