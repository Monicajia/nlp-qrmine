import numpy
from imblearn.over_sampling import RandomOverSampler
from keras.layers import Dense
from keras.models import Sequential
from numpy import random, argsort, sqrt, array, ones
from pandas import read_csv
from sklearn.cluster import KMeans
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier


class MLQRMine(object):

    def __init__(self):
        self._seed = 7
        self._csvfile = ""
        self._dataset = None
        self._X = None
        self._y = None
        self._X_original = None
        self._y_original = None
        self._dataset_original = None
        self._model = Sequential()
        self._sc = StandardScaler()
        self._vnum = 0  # Number of variables
        self._classifier = XGBClassifier()
        self._epochs = 10
        self._samplesize = 0

    @property
    def seed(self):
        return self._seed

    @property
    def csvfile(self):
        return self._csvfile

    @property
    def dataset(self):
        return self._dataset

    @property
    def model(self):
        return self._model

    @property
    def epochs(self):
        return self._epochs

    @property
    def X(self):
        return self._X

    @property
    def y(self):
        return self._y

    # Getters should be before setters*
    @epochs.setter
    def epochs(self, epochs):
        self._epochs = epochs

    @seed.setter
    def seed(self, seed):
        self._seed = seed

    @csvfile.setter
    def csvfile(self, csvfile):
        self._csvfile = csvfile

    # Functions
    def read_csv(self):
        self._dataset = read_csv(self._csvfile, header=1)

    def mark_missing(self):
        self._dataset_original = self._dataset
        self._dataset = self._dataset.replace('', numpy.NaN)
        self._dataset.dropna(inplace=True)

    def restore_mark_missing(self):
        self._dataset = self._dataset_original

    def get_shape(self):
        return self._dataset.shape

    """
    The actual number of IVs is vnum -2 as first is the title and the last is the DV
    To seperate DV, use vnum -1 to indicate last column
    More details on np array splicing here: 
    https://stackoverflow.com/questions/34007632/how-to-remove-a-column-in-a-numpy-array/34008274
    """
    def read_xy(self):
        (self._samplesize, vnum) = self._dataset.shape
        # Last column in the csv should be the DV and first one is title (So get the number of variables)
        self._vnum = vnum - 2
        # splice into IVs and DV
        values = self._dataset.values
        # self._X = values[:, 0:self._vnum]
        # First column ignored - (To be used for title)
        self._X = values[:, 1:vnum - 1]
        self._y = values[:, vnum - 1]

    def oversample(self):
        self._X_original = self._X
        self._y_original = self._y
        ros = RandomOverSampler(random_state=0)
        X, y = ros.fit_sample(self._X, self._y)
        self._X = X
        self._y = y

    def restore_oversample(self):
        self._X = self._X_original
        self._y = self._y_original

    def prepare_data(self):
        self.read_csv()
        self.mark_missing()
        self.read_xy()
        self.oversample()

    def get_nnet_predictions(self):
        self._model.add(Dense(12, input_dim=self._vnum, kernel_initializer='uniform', activation='relu'))
        self._model.add(Dense(8, kernel_initializer='uniform', activation='relu'))
        self._model.add(Dense(1, kernel_initializer='uniform', activation='sigmoid'))
        # Compile model
        self._model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
        # Fit the model
        self._model.fit(self._X, self._y, epochs=self._epochs, batch_size=10, verbose=2)

        # calculate predictions
        predictions = self._model.predict(self._X_original)
        # round predictions
        rounded = [round(x[0]) for x in predictions]
        return rounded

    def get_nnet_scores(self):
        return self._model.evaluate(self._X, self._y)

    def svm_confusion_matrix(self):
        X_train, X_test, y_train, y_test = train_test_split(self._X, self._y, test_size=0.25, random_state=0)
        X_train = self._sc.fit_transform(X_train)
        X_test = self._sc.transform(X_test)
        classifier = SVC(kernel='linear', random_state=0)
        classifier.fit(X_train, y_train)
        y_pred = classifier.predict(X_test)
        return confusion_matrix(y_test, y_pred)

    def knn_search(self, K=3, x=None):
        """ find K nearest neighbours of data among D """
        D = self._X_original
        if x is None:
            x = self._X_original[[0], :]

        ndata = D.shape[1]
        K = K if K < ndata else ndata
        # euclidean distances from the other points
        sqd = sqrt(((D - x[:, :ndata]) ** 2).sum(axis=0))
        idx = argsort(sqd)  # sorting
        # return the indexes of K nearest neighbours

        return idx[:K]

    def get_kmeans(self):
        kmeans = KMeans(n_clusters=5, init='k-means++', random_state=42)
        y_kmeans = kmeans.fit_predict(self._X)
        return y_kmeans

    def encode_categorical(self):
        labelencoder_X_1 = LabelEncoder()
        self._X[:, 1] = labelencoder_X_1.fit_transform(self._X[:, 1])
        labelencoder_X_2 = LabelEncoder()
        self._X[:, 2] = labelencoder_X_2.fit_transform(self._X[:, 2])
        onehotencoder = OneHotEncoder(categorical_features=[1])
        X = onehotencoder.fit_transform(self._X).toarray()
        X = X[:, 1:]
        self._X = X

    def get_association(self):
        X_train, X_test, y_train, y_test = train_test_split(self._X, self._y, test_size=0.25, random_state=0)
        self._classifier.fit(X_train, y_train)

        # Predicting the Test set results
        y_pred = self._classifier.predict(X_test)
        return confusion_matrix(y_test, y_pred)