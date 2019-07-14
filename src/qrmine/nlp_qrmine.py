import subprocess
import textacy
from textacy.vsm.vectorizers import Vectorizer
import textacy.tm

class Qrmine(object):

    def __init__(self):
        self._min_occurrence_for_topic = 2
        self._common_verbs = 10
        # create an empty corpus
        self._en = textacy.load_spacy_lang('en_core_web_sm', disable=('parser',))
        self._corpus = textacy.Corpus(lang=self._en)
        self._content = None
        self._model = None
        self._numdocs = 0
        self._numtopics = 0
        self._terms = None
        self._doc_term_matrix = None
        self._doc_topic_matrix = None
        self._vectorizer = Vectorizer(tf_type='linear', apply_idf=True, idf_type='smooth',
                                      norm='l2', min_df=3, max_df=0.95, max_n_terms=100000)

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        self._content = content

    def min_topic(self, min_topic):
        self._min_occurrence_for_topic = min_topic

    def common_verbs(self, common_verbs):
        self._common_verbs = common_verbs

    @staticmethod
    def print_table(table):
        col_width = [max(len(x) for x in col) for col in zip(*table)]
        for line in table:
            print("| " + " | ".join("{:{}}".format(x, col_width[i])
                                    for i, x in enumerate(line)) + " |")

    @property
    def get_git_revision_hash(self):
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'])

    @property
    def get_git_revision_short_hash(self):
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode("utf-8")
        # return subprocess.check_output(['git', 'log', '-1', '--format=%cd']).strip().decode("utf-8")[10:]

    def print_categories(self, doc, num=10):
        bot = doc._.to_bag_of_terms(ngrams=(1, 2, 3), named_entities=False, normalize='lemma', weighting='freq',
                                    as_strings=True, filter_stops=True, filter_punct=True, filter_nums=True, min_freq=2,
                                    drop_determiners=True, include_types=["NOUN", "VERB"])
        categories = sorted(bot.items(), key=lambda x: x[1], reverse=True)[:num]
        output = []
        to_return = []
        print("\n---Categories with count---")
        output.append(("CATEGORY", "WEIGHT"))
        for category, count in categories:
            output.append((category, str(count)))
            to_return.append(category)
        self.print_table(output)
        print("---------------------------\n")
        return to_return

    def print_topics(self, numtopics=0):
        if numtopics > 0:
            self._numtopics = numtopics
        topic_list = list(range(1, self._numtopics))
        output = []
        print("\n---Topics---")
        output.append(("TOPIC", "DESCRIPTION"))
        for topic_idx, top_terms in self._model.top_topic_terms(self._vectorizer.id_to_term, topics=topic_list):
            output.append(("TOPIC:" + str(topic_idx), '   '.join(top_terms)))
        self.print_table(output)
        print("---------------------------\n")

    # https://www.pydoc.io/pypi/textacy-0.4.0/autoapi/tm/topic_model/index.html
    # Rem stop words http://ai.intelligentonlinetools.com/ml/category/topic-modeling/
    # To set Top N
    def print_documents(self, top_n=2):
        topic_list = list(range(1, self._numtopics))
        output = []
        print("\n---Topics---")
        output.append(("TOPIC", "DOCUMENTS"))
        for topic_idx, top_docs in self._model.top_topic_docs(self._doc_topic_matrix, topics=topic_list,
                                                              top_n=top_n):
            str_topic_idx = str(topic_idx)
            for j in top_docs:
                # output.append((str_topic_idx, self._corpus[j].metadata['title']))
                output.append((str_topic_idx, self._corpus.docs[j]._.meta["title"]))
                str_topic_idx = "..."
        self.print_table(output)
        print("---------------------------\n")
        print("\n---Documents To Topics---")
        for doc_idx, topics in self._model.top_doc_topics(self._doc_topic_matrix, docs=range(self._numdocs),
                                                          top_n=top_n):
            # print(self._corpus[doc_idx].metadata['title'], ':', topics)
            print(self._corpus.docs[doc_idx]._.meta["title"], ':', topics)
        print("---------------------------\n")

    def print_dict(self, content, num=10):
        output = []
        print("\n---Coding Dictionary---")
        output.append(("CATEGORY", "PROPERTY", "DIMENSION"))
        words = content.common_verbs(num)
        for word, f1 in words:
            for attribute, f2 in content.attributes(word, 3):
                for dimension, f3 in content.dimensions(attribute, 3):
                    output.append((word, attribute, dimension))
                    word = '...'
                    attribute = '...'

        self.print_table(output)
        print("---------------------------\n")

    def process_content(self):
        if self._content is not None:
            ct = 0
            for document in self._content.documents:
                metadata = {}
                try:
                    metadata['title'] = self._content.titles[ct]
                except IndexError:
                    metadata['title'] = 'Empty'
                # self._corpus.add_text(textacy.preprocess_text(document, lowercase=True, no_punct=True, no_numbers=True),
                #                       metadata=metadata)
                doc_text = textacy.preprocess_text(document, lowercase=True, no_punct=True, no_numbers=True)
                doc = textacy.make_spacy_doc((doc_text, metadata), lang=self._en)
                self._corpus.add_doc(doc)
            self.load_matrix()

    def filter_content(self, titles):
        if self._content is not None:
            ct = 0
            for document in self._content.documents:
                metadata = {}
                try:
                    if any(self._content.titles[ct] in s for s in titles):
                        metadata['title'] = self._content.titles[ct]
                        # self._corpus.add_text(
                        #     textacy.preprocess_text(document, lowercase=True, no_punct=True, no_numbers=True),
                        #     metadata=metadata)
                        doc_text = textacy.preprocess_text(document, lowercase=True, no_punct=True, no_numbers=True)
                        doc = textacy.make_spacy_doc((doc_text, metadata), lang=self._en)
                        self._corpus.add_doc(doc)

                except IndexError:
                    metadata['title'] = 'Empty'

                ct += 1
            self.load_matrix()

    def load_matrix(self):
        self._doc_term_matrix = self._vectorizer.fit_transform(
            (documents._.to_terms_list(ngrams=(1, 2, 3), named_entities=True,
                                     as_strings=True, filter_stops=True,
                                     filter_punct=True, filter_nums=True,
                                     min_freq=1)
             for documents in self._corpus.docs))
        self._numdocs, self._terms = self._doc_term_matrix.shape
        self._model = textacy.tm.TopicModel('nmf', n_topics=self._numdocs)
        self._model.fit(self._doc_term_matrix)

        self._doc_topic_matrix = self._model.transform(self._doc_term_matrix)

        _, self._numtopics = self._doc_topic_matrix.shape
