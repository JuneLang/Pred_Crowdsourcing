import numpy
import math
import sklearn

class RaykarClassifier(object):
    """Classifier based on the Raykar et al. (2010) EM algorithm.

    Jointly learns an annotator model and a classification model.
    """

    def __init__(self, n_restarts=5, epsilon=1e-5):
        """
        n_restarts: Number of times to run the algorithm. Higher numbers improve
            chances of finding a global maximum likelihood solution.
        epsilon: Convergence threshold.
        lr_init: Whether to initialise w using logistic regression.
        """
        self.n_restarts = n_restarts
        self.epsilon = epsilon

    def init_parameters(self, mv):
        """

        :param mv: list of results of majority of voting
        :return:
        """

    def run(self, y):
        # Compute majority vote labels for initialisation.
        mv = majority_vote(y)
        m = mv.copy()
        # Add a small random factor for variety.
        m[m == 1] -= numpy.abs(numpy.random.normal(scale=1e-2,
                                                   size=m[m == 1].shape[0]))
        m[m == 0] += numpy.abs(numpy.random.normal(scale=1e-2,
                                                   size=m[m == 0].shape[0]))

        # Convert y into a dense array and a mask. Then we can ignore the mask
        # when we don't need it and get nice fast code (numpy.ma is quite slow).
        y_mask = y.mask
        y_1 = y.filled(1)
        y = y_0 = y.filled(0)

        for trial in range(self.n_restarts):

            m = self.m_step()
            self.e_step()

    def m_step(self, m, y, y_mask):
        """
        :param pr:
        :param y: (n_labllers, m_examples)
        :return:
        """
        a = numpy.zeros((y.shape[0],))
        reciprocal = numpy.ones((y.shape[0]))
        for t in range(y.shape[0]):
            for i in range(y.shape[1]):
                if y_mask[t, i]:
                    continue

                a[t] += (m[i] - y[t, i]) * (m[i] - y[t, i])
                # divisor[t] += m[i]

        # divisor[divisor == 0] = EPS
        return reciprocal / (a / y.shape[1])

    def e_step(self, a, m, y, y_mask):
        """

        :return:
        """
        for i in range(m.shape[0]):
            sum_a = numpy.sum(a)
            for j in range(a.shape[0]):
                if y_mask[i, j]:
                    continue
                m[i] += a[j] * y[i, j] / sum_a


if __name__ == '__main__':
