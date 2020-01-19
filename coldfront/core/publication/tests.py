import itertools
from django.test import TestCase

from coldfront.core.test_helpers.factories import (
    ProjectFactory,
    PublicationSourceFactory,
)
from coldfront.core.publication.models import Publication
from coldfront.core.publication.views import PublicationSearchResultView


class TestPublication(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            project = ProjectFactory()
            source = PublicationSourceFactory()

            self.initial_fields = {
                'project': project,
                'title': 'Test publication!',
                'author': 'coldfront et al.',
                'year': 1,
                'journal': 'Wall of the North',
                'unique_id': '5/10/20',
                'source': source,
                'status': 'Active',
            }

            self.unsaved_publication = Publication(**self.initial_fields)

            self.journals = [
                'First academic journal of the world',
                'Second academic journal of the world',
                'New age journal',
            ]

    def setUp(self):
        self.data = self.Data()
        self.unique_id_generator = ('unique_id_{}'.format(id) for id in itertools.count())

    def test_fields_generic(self):
        self.assertEqual(0, len(Publication.objects.all()))

        pub = self.data.unsaved_publication
        pub.save()

        retrieved_pub = Publication.objects.get(pk=pub.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_pub, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(pub, retrieved_pub)

    def test_journal_edits(self):
        pub = self.data.unsaved_publication
        pub.save()

        journals = self.data.journals

        for journal in journals:
            with self.subTest(item=journal):
                pub.journal = journal
                pub.save()

                retrieved_pub = Publication.objects.get(pk=pub.pk)
                self.assertEqual(journal, retrieved_pub.journal)
                self.assertEqual(pub, retrieved_pub)

        all_pubs = Publication.objects.all()
        self.assertEqual(1, len(all_pubs))

    def test_journal_unique_publications(self):
        fields = self.data.initial_fields
        journals = self.data.journals

        for journal in journals:
            with self.subTest(item=journal):
                these_fields = fields.copy()
                these_fields['journal'] = journal
                these_fields['unique_id'] = next(self.unique_id_generator)

                pub, created = Publication.objects.get_or_create(**these_fields)
                self.assertEqual(True, created)
                self.assertEqual(these_fields['journal'], pub.journal)

        all_pubs = Publication.objects.all()
        self.assertEqual(len(journals), len(all_pubs))
        self.assertNotEqual(0, len(all_pubs))


class TestDataRetrieval(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            self.expected_pubdata = [
                {
                    'unique_id': '10.1038/s41524-017-0032-0',
                    'title': 'Construction of ground-state preserving sparse lattice models for predictive materials simulations',
                    'author': 'Wenxuan Huang and Alexander Urban and Ziqin Rong and Zhiwei Ding and Chuan Luo and Gerbrand Ceder',
                    'year': '2017',
                    'journal': 'npj Computational Materials',
                },
            ]

            # everything we might test will use this source
            source = PublicationSourceFactory()
            for pubdata_dict in self.expected_pubdata:
                pubdata_dict['source_pk'] = source.pk

    def setUp(self):
        self.data = self.Data()

    def run_target_method(self, unique_id, *args, **kwargs):
        target_method = PublicationSearchResultView._search_id

        # this method is defined as an instance method but doesn't use any instance data
        # thus, we use None for its 'self' argument
        return target_method(None, unique_id, *args, **kwargs)

    def test_doi_retrieval(self):
        expected_pubdata = self.data.expected_pubdata

        self.assertNotEqual(0, len(expected_pubdata))  # check assumption
        for pubdata_dict in expected_pubdata:
            unique_id = pubdata_dict['unique_id']
            with self.subTest(unique_id=unique_id):
                retrieved_data = self.run_target_method(unique_id)
                self.assertEqual(pubdata_dict, retrieved_data)
