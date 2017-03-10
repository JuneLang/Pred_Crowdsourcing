Pred_Crowdsourcing
===

#Introduction
This application is using `Majority Voting` and `Raykar`(not yet finished) to find the consensus among several transcriptions from several workers.

#Structure
The main class is `MajorityVoting` in the file *Test.py*. It reads the json file as input, and produce an output json file which contains the consensus.
The class `Label` contains all the information about a label.
The class `User` contains all the information about an user.
The class `RaykarClassifier` runs the Rarkar algorithm.

#Data format
##Input
The Data format is almost the same with the one of the "emigrant"(as mentioned in the report), while in "emigrant" a page is stored in one file and in out projet is all stored in one single file.
##Output
Almost the same with the input, while it abandon some informations not nessesary for the algorithm, and append some informations after the excution of the algorithm, like:
>`normalized_version`: the string of proposition after lossless normalization;

#Install the libraries (dependencies)
We are using [Python 3.5.2](https://www.python.org/downloads/release/python-352/).
And we use [Anaconda](https://www.continuum.io/downloads) for package and environment control(strongly recommended for Windows, because `scipy` is difficult to be installed in Windows. And it is also good for Linux or Mac).
Download and install `Anaconda` and typing the commands in the terminal: `conda update conda` and `conda update anaconda`. If they are excuted successfully, it means `Annaconda` is good to work.
Then using it to install the packages.
>[numpy](http://www.numpy.org/); To install it, use `conda install --name root numpy` to install or update it in the root environment.
>[scipy](http://www.scipy.org/install.html); Use `conda install --name root scipy` to install or update.
>[matplotlib](http://matplotlib.org/); Use `conda install --name root matplotlib` to install or update.
>[seaborn](http://seaborn.pydata.org/); Use `conda install --name root seaborn` to install or update.

#How it works 

##Run Majority Voting
Simply, initiate the class `MajorityVoting' specifying the input file (json) and the minimal number of votes(not required, is not set, is 1 by default).
    getConsensus = MajorityVoting(input_json, number_votes)
And then, set the ouput folder to stored the result:
    getConsensus.setOutputFolder(output_folder)
And then, set the seuil for finding the consensus. If this function is not called, the seuil is set to 0.5 by default:
    getConsensus.set_seuil(seuil)
Last, run the class:
    getConsensus.calculateConsensus()
The result will be stored in the ouput folder.

##Plot the analyses
After the result is produced, we can call the functions for analyse and then plot the analyse. Using matplotlib, it seems that if we call multiple `plot.show()` to plot different figurs at the same time, it can not plot them at the same time, but it can plot one by one if we close the window which showing the privous figure (and then the next one comes out).

###plot_seuil
Call the function `plot_seuil()` is to plot the histogram to show the distribution of ratio of the consensus. For exemple, we have 81% consensus with the seuil set as 0.5. The red bar indicates that after this ratio we loss visibly consensus found.

###chronology
Call the function `chronology()` is to analyze the chronology and plot 2 charts. The first one is the orginal histogram as the function `plot_seuil()` plots, and the second one is the histogram after chronology with a line indicating the difference between them.

###plot_propositions
Call the function `plot_propositions()` plots a histogram showing that the number of labels having consensus "group by" the number of propositions of the label. It automatically ignores the label with only one propositions because with only one proposition we can be sure that the label do have a consensus. Each bar represents a proposition, and it is devised into 4 parts. The first 3 parts (at the bottom) indicates the number of labels "group by" the total votes of the label. The last part shows the number of labels remaining.

###plot_proposition
Call the function `plot_propositions(seuil, plot_range)` to plot the distribution of labels (to see how many labels reach consensus with seuil and with different numbers of propositions).
>`seuil`: the seuil of consensus;
>`plot_range`: the range of the number of propositions. For example, using `range(5)` as `plot_range` means to plot 2 to 6 propositions.


