# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
import itertools
from unittest.mock import Mock, patch, sentinel

import bibtexparser.bibdatabase
import bibtexparser.bparser
import doi2bib
from django.test import TestCase

import coldfront.core.publication
from coldfront.core.publication.models import Publication
from coldfront.core.publication.views import PublicationSearchResultView
from coldfront.core.test_helpers.decorators import (
    makes_remote_requests,
)
from coldfront.core.test_helpers.factories import (
    ProjectFactory,
    PublicationSourceFactory,
)


class TestPublication(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            project = ProjectFactory()
            source = PublicationSourceFactory()

            self.initial_fields = {
                "project": project,
                "title": "Test publication!",
                "author": "coldfront et al.",
                "year": 1,
                "journal": "Wall of the North",
                "unique_id": "5/10/20",
                "source": source,
                "status": "Active",
            }

            self.unsaved_publication = Publication(**self.initial_fields)

            self.journals = [
                "First academic journal of the world",
                "Second academic journal of the world",
                "New age journal",
            ]

    def setUp(self):
        self.data = self.Data()
        self.unique_id_generator = ("unique_id_{}".format(id) for id in itertools.count())

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
                these_fields["journal"] = journal
                these_fields["unique_id"] = next(self.unique_id_generator)

                pub, created = Publication.objects.get_or_create(**these_fields)
                self.assertEqual(True, created)
                self.assertEqual(these_fields["journal"], pub.journal)

        all_pubs = Publication.objects.all()
        self.assertEqual(len(journals), len(all_pubs))
        self.assertNotEqual(0, len(all_pubs))


class TestDataRetrieval(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        NO_JOURNAL_INFO_FROM_DOI = "[no journal info from DOI]"

        def __init__(self):
            self.expected_pubdata = [
                {
                    "unique_id": "10.1038/s41524-017-0032-0",
                    "title": "Construction of ground-state preserving sparse lattice models for predictive materials simulations",
                    "author": "Wenxuan Huang and Alexander Urban and Ziqin Rong and Zhiwei Ding and Chuan Luo and Gerbrand Ceder",
                    "year": "2017",
                    "journal": "npj Computational Materials",
                },
                {
                    "unique_id": "10.1145/2484762.2484798",
                    "title": "The institute for cyber-enabled research",
                    "author": "Dirk Colbry and Bill Punch and Wolfgang Bauer",
                    "year": "2013",
                    "journal": self.NO_JOURNAL_INFO_FROM_DOI,
                },
            ]

            # everything we might test will use this source
            source = PublicationSourceFactory()
            for pubdata_dict in self.expected_pubdata:
                pubdata_dict["source_pk"] = source.pk

    class Mocks:
        """Set of mocks for testing, for simplified setup in test cases

        Our app uses multiple libraries together to provide us with data in a
        form we can consume.
        This class acts to encapsulate mocking and patching those libraries -
        focusing tests instead on the post-library data that the app would be
        using."""

        def __init__(self, bibdatabase_first_entry, unique_id):
            self._bibdatabase_first_entry = bibdatabase_first_entry.copy()
            self._unique_id = unique_id

            def mock_get_bib(unique_id):
                # ensure specified unique_id is used here
                if unique_id == self._unique_id:
                    return sentinel.status, sentinel.bib_str

            crossref = Mock(spec_set=doi2bib.crossref)
            crossref.get_bib.side_effect = mock_get_bib

            def mock_parse(thing_to_parse):
                # ensure bib_str from get_bib() is used
                if thing_to_parse is sentinel.bib_str:
                    bibdatabase_cls = Mock(spec_set=bibtexparser.bibdatabase.BibDatabase)
                    db = bibdatabase_cls()
                    db.entries = [self._bibdatabase_first_entry.copy()]
                    return db

            bibtexparser_cls = Mock(spec_set=bibtexparser.bparser.BibTexParser)
            bibtexparser_cls.return_value.parse.side_effect = mock_parse

            as_text = Mock(spec_set=bibtexparser.bibdatabase.as_text)
            as_text.side_effect = lambda bib_entry: "as_text({})".format(bib_entry)

            self.crossref = crossref
            self.bibtexparser_cls = bibtexparser_cls
            self.as_text = as_text

        @contextlib.contextmanager
        def patch(self):
            def dotpath(qualname):
                module_under_test = coldfront.core.publication.views
                return "{}.{}".format(module_under_test.__name__, qualname)

            with contextlib.ExitStack() as stack:
                patches = [
                    patch(dotpath("BibTexParser"), new=self.bibtexparser_cls),
                    patch(dotpath("crossref"), new=self.crossref),
                    patch(dotpath("as_text"), new=self.as_text),
                ]
                for p in patches:
                    stack.enter_context(p)
                yield

    def setUp(self):
        self.data = self.Data()

    def run_target_method(self, unique_id, *args, **kwargs):
        target_method = PublicationSearchResultView._search_id

        # this method is defined as an instance method but doesn't use any instance data
        # thus, we use None for its 'self' argument
        return target_method(None, unique_id, *args, **kwargs)

    @makes_remote_requests()
    def test_doi_retrieval(self):
        # NOTE: this test does not use any mocks
        expected_pubdata = self.data.expected_pubdata

        self.assertNotEqual(0, len(expected_pubdata))  # check assumption
        for pubdata_dict in expected_pubdata:
            unique_id = pubdata_dict["unique_id"]
            with self.subTest(unique_id=unique_id):
                retrieved_data = self.run_target_method(unique_id)
                self.assertEqual(pubdata_dict, retrieved_data)

    def test_doi_extraction(self):
        for pubdata in self.data.expected_pubdata:
            testdata = pubdata.copy()  # several adjustments required, below

            # test cases with NO_JOURNAL_INFO_FROM_DOI need more setup, done later in context
            is_nojournal_test = testdata["journal"] == self.data.NO_JOURNAL_INFO_FROM_DOI

            # mutate test data so that it's definitely nonrealistic, thus
            # assuring that we *are* mocking the right stuff
            for k in (k for k in testdata if k != "source_pk"):
                testdata[k] += "[not real]"

            unique_id = testdata["unique_id"]

            # source_pk doesn't pertain to data returned from the remote api
            mocked_bibdatabase_entry = testdata.copy()
            del mocked_bibdatabase_entry["source_pk"]

            # for no-journal tests, we emulate not having any 'journal' key in
            # data returned from remote api
            if is_nojournal_test:
                del mocked_bibdatabase_entry["journal"]

            mocks = self.Mocks(mocked_bibdatabase_entry, unique_id)

            # need to transform our expected data to check mock calls
            expected_data = testdata.copy()
            mock_as_text = mocks.as_text.side_effect

            # we expect `as_text` to be run on...
            as_text_expected_on = ["author", "title", "year"]
            if not is_nojournal_test:
                as_text_expected_on.append("journal")

            for key in as_text_expected_on:
                transformed = mock_as_text(expected_data[key])

                # check assumptions: the transformation is meaningful
                assert transformed
                assert transformed != expected_data[key]

                expected_data[key] = transformed

            # for no-journal tests, we expect a special string
            if is_nojournal_test:
                expected_data["journal"] = self.data.NO_JOURNAL_INFO_FROM_DOI

            # finally done with setup... now to run the test...
            with self.subTest(unique_id=unique_id):
                with mocks.patch():
                    retrieved_data = self.run_target_method(unique_id)
                self.assertEqual(expected_data, retrieved_data)
