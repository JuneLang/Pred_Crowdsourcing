import numpy
import math
import sklearn
import time

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

    def init_parameters(self, mv, y, y_labels):
        """

        :param mv: list of results of majority of voting
        :param y: (n_workers, m_labels)
        :param y_labels: list of labels
        :return:
        """
        self.mv = mv
        self.y = y
        self.y_labels = y_labels

    def run(self, mv, y):
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
        iter_results = []
        for trial in range(self.n_restarts):
            a = numpy.zeros((y.shape[0],), dtype=float)
            m_new = numpy.zeros((m.shape[0],), dtype=float)

            while True:
                then = time.time()

                a = self.m_step(m, y, y_mask)
                m_new = self.e_step(a, m, y, y_mask)
                dm = numpy.linalg.norm(m_new - m)

                if dm < self.epsilon:
                    iter_results.append((a, m_new))

                m = m_new

                # Estimate time remaining.
                now = time.time()
                dt = now - then
                print('Raykar iteration took {} s.'.format(dt))



    def m_step(self, m, y, y_mask):
        """
        :param pr:
        :param y: (n_labllers, m_examples)
        :return:
        """
        a = numpy.zeros((y.shape[0],), dtype=float)
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
        m_new = numpy.zeros((m.shape[0],), dtype=float)
        for i in range(m.shape[0]):
            sum_a = numpy.sum(a)
            for j in range(a.shape[0]):
                if y_mask[i, j]:
                    continue
                m_new[i] += a[j] * y[i, j] / sum_a
        return m_new


if __name__ == '__main__':
    print()
