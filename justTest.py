import numpy
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime
import difflib
import string

# # sns.set_style(style="ticks")
# x = np.array([2, 2, 4, 5])
# y = [1, 2, 3, 4, 5]
# y1 = [1, 1, 1]
# fig, ax = plt.subplots()
# for a in [y, y1, x]:
#     sns.distplot(a, bins=range(1, 7, 1), ax=ax, kde=False)
#
# ax.set_xlim([1, 6])
# # y2 = np.array([2])
# # plt.hist(x, y2, normed=True, color="#FF0333")
# # y3 = np.array([3])
# # plt.hist(x, y3, normed=True, color="#FF1234")
# # plt.xlabel("ratio")
# # plt.ylabel("consensus%")
# plt.show()
s1 = "Mrs. Sylvia Parmentier"
s2 = "Mm Sylvia Parmentin"

trans = str.maketrans('', '', string.punctuation)
s1 = s1.translate(trans)
s2 = s2.translate(trans)
seq = difflib.SequenceMatcher(None, s1, s2)
print(seq.ratio())
