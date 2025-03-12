from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class AnnouncementMailingListChoice(TimeStampedModel):

    class Meta:
        ordering = ['name', ]

    class AnnouncementMailingListChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64)
    value = models.EmailField(max_length=64)
    subcribed = models.ManyToManyField(User, blank=True)
    objects = AnnouncementMailingListChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

class AnnouncementCategoryChoice(TimeStampedModel):

    class Meta:
        ordering = ['name', ]

    class AnnouncementCategoryChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64)
    objects = AnnouncementCategoryChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    def get_mailing_lists(self):
        return self.mailinglists_set.filter()


class AnnouncementStatusChoice(TimeStampedModel):

    class Meta:
        ordering = ['name', ]

    class AnnouncementStatusChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64)
    objects = AnnouncementStatusChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class Announcement(TimeStampedModel):

    class Meta:
        ordering = ['created', ]

    title = models.CharField(max_length=255)
    body = models.TextField()
    categories = models.ManyToManyField(AnnouncementCategoryChoice, blank=True)
    status = models.ForeignKey(AnnouncementStatusChoice, on_delete=models.CASCADE)
    viewed_by = models.ManyToManyField(User, related_name='viewed_by', blank=True)
    pinned = models.BooleanField(default=False)
    mailing_lists = models.ManyToManyField(AnnouncementMailingListChoice, blank=True)
    details_url = models.URLField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    history = HistoricalRecords()
