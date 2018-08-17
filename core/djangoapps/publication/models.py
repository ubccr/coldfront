from django.db import models

    project = models.ForeignKey(Project)
    title = models.CharField(max_length=1024)
    author = models.CharField(max_length=1024)
    date = models.CharField(
        validators=[MaxLengthValidator(100)],
        max_length=100,
        verbose_name='Publication Date',
        null=True,
        blank=True,
    )

    trueauthor = models.CharField(
        validators=[MinLengthValidator(2), MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    ams_subject = models.CharField(
        validators=[MinLengthValidator(3), MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    review = models.CharField(
        validators=[MinLengthValidator(3), MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    pages = models.CharField(
        validators=[MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    booktitle = models.CharField(
        validators=[MinLengthValidator(5), MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    publisher = models.CharField(
        validators=[MinLengthValidator(2), MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    series = models.CharField(
        validators=[MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    journal = models.CharField(
        validators=[MinLengthValidator(5), MaxLengthValidator(255)],
        max_length=255,
        null=True,
        blank=True,
    )

    volume = models.CharField(
        validators=[MaxLengthValidator(100)],
        max_length=255,
        null=True,
        blank=True,
    )

    fromwhere = models.CharField(
        validators=[MinLengthValidator(5), MaxLengthValidator(100)],
        max_length=255,
        null=True,
        blank=True,
    )

    doi = models.CharField(
        'DOI',
        validators=[MinLengthValidator(4), MaxLengthValidator(1024)],
        max_length=1024,
        null=True,
        blank=True,
    )

    full_citation = models.TextField(
        validators=[MinLengthValidator(5)],
        null=True,
        blank=True,
    )

    PUBLICATION_ACTIVE = 'ACTIVE'
    PUBLICATION_ARCHIVED = 'ARCHIVED'

    STATUS_CHOICES = (
        (PUBLICATION_ACTIVE, PUBLICATION_ACTIVE),
        (PUBLICATION_ARCHIVED, PUBLICATION_ARCHIVED),
    )

    status = models.CharField(
        validators=[MinLengthValidator(3), MaxLengthValidator(25)],
        max_length=25,
        choices=STATUS_CHOICES,
        default=PUBLICATION_ACTIVE,
    )
