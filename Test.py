# test codes
from Label import Label
import json
from difflib import ndiff
from math import floor
import argparse
import collections
import os
import re
import time

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

"""
    An aggregate map class. self.total represents the total number of
    items in the self.aggMap. self.aggMap is a map of string to the frequency
    these words were encountered. In the context of this problem, AggMap is
    used to group words that a similar. Only words who are in the majority
    AggMap will be considered as a solution to the consensus.
"""


class AggMap:
    def __init__(self):
        self.total = 0
        self.aggMap = collections.defaultdict(int)

    # @property
    def __repr__(self):
        return str(self.total) + str(self.aggMap)


class Consensus(object):
    def __init__(self, inputFile, mv):
        # Indicates if output is verbose for debugging
        self.debug = False

        # Input json file
        self.input_json = self.read_inputJson(inputFile)

        # Output json; initialize by copy the input
        self.output_pages = []
        self.seuil = 0.5  # by default

        # Minimum workers required
        self.min_votes = mv

        # Label that consensus entries are grouped by
        # self.keyLabel = self.getKeyLabel()
        # Output folder
        self.outputFolder = None
        # Indicates if lossless custom functions are to be used for normalizing data
        self.useFunctionNormalizer = False
        # Indicates if lossless translation tables are to be used for normalizing data
        self.useTranslationNormalizer = False
        # Indicates if voting is done as (top group/total entries) "False" or
        #                                (top group > second top group) "True"
        self.top2 = False

        # Maps the labels to the translation tables and dictionaries they will
        # need
        self.labelMap = None
        # Labels to find a consensus for
        # self.labels = labelMap.keys()
        self.labels_by_page = self.get_labels_by_page()

        # The current translation table
        self.translationTable = None
        self.translationTables = None
        # The current spell correction dictionary
        self.correctionDictionary = None

        # String cleaner
        # Can be decorated for more functionality
        # Adds the PLSS cleaner by default
        self.clean = self._noChange
        self.lossyClean = self._noChange
        # Exact String comparator - originally does only exact match
        # Can be decorated for more functionality
        self.comparator = self._exactMatch
        # Approximate string comparator
        self.approx = self._exactMatch

        # Punctuation to ignore
        # The first list removes general punctuation, the second removes punctuation if
        # not part of a number (ex: 20.99 -> 20.99, but other periods will be removed)
        self.puncPattern = re.compile(r"[\\,&\"(#)!?$:;'-]|([\./](?!\d))")

        # Flag to ignore empty strings
        self.ignoreEmptyStrings = False

        # Default responses to replace with self.defaultResponse
        self.ignoreDefaults = False
        self.defaultResponse = 'unknown'
        self.defaultResponsesToReplace = ['placeholder', 'unknown', 'Unknown',
                                          'not given', 'n/a', 'no data', 'nil', '']
        # The list of regex to detect unknown responses include: single lower
        # case letters and symbols, repeated characters (2 or more),
        # different types of unknowns (sn, na, none), only non-characters
        self.defaultRegexResponsesToReplace = ["^[-\\!?'\".a-z]$", "^([^0-9])\\1+$", \
                                               "^[uU]nknown .+$", "^[sS][. ]?[nN][.]?$", "^[nN][./ ]?[aA][./]?$", \
                                               "^[Nn][Oo][Nn][Ee][ ]?[\w?]*$", "^[-\\!?'\"., ]+$"]

        # Stopwords that can be ignored in a response
        self.stopwords = ['a', 'an', 'if', 'it', 'its', 'of', 'than',
                          'that', 'the', 'to']

        # Define a regex to normal Public Lands Survey System Notation:
        # http://faculty.chemeketa.edu/afrank1/topo_maps/town_range.htm
        # define township match
        patternHead = '(?P<town>[T])(\.)?(\s)?(?P<townN>[0-9]+)(\s)?'
        patternHead += '(?P<townD>[NEWS])'
        patternHead += '|'
        # define the optional subsection match
        patternMid = '(?P<sub>(([NEWS./]{1,4})(\s)?((1/4)|(1/2)|Q,)(\s?)(of)?(\s?))+)'
        # define section match
        patternTail = '(?P<sec>Sec?)([.,])?(\s)?(?P<secN>[0-9]+)'
        patternTail += '|'
        # define range match
        patternTail += '(?P<range>R)(\.)?(\s)?(?P<rangeN>[0-9]+)(\s)?'
        patternTail += '(?P<rangeD>[NEWS])[.,;]?'
        # pattern WITH NO subsection match
        pattern = patternHead + patternTail
        # pattern WITH subsection match
        patternWSub = patternHead + patternMid + patternTail
        # define separator between occurrences
        pattern = '((' + pattern + ')(\s)?([.,;])?(\s)?)'
        patternWSub = '((' + patternWSub + ')(\s)?([.,;]?)?(\s)?)'
        # define min number of occurrences
        pattern = '(' + pattern + '{3,})(?P<close>([)]?))'
        patternWSub = '(' + patternWSub + '{3,})(?P<close>([)]?))'
        # Precompile the regex pattern for string with NO optional subsections
        self.plssRegex = re.compile(pattern, flags=re.IGNORECASE)
        self.plssReplace = '\\g<sec> \\g<secN>, '
        self.plssReplace += '\\g<town>\\g<townN>\\g<townD>, '
        self.plssReplace += '\\g<range>\\g<rangeN>\\g<rangeD>.'
        # Precompile the regex pattern for string WITH optional subsections
        self.plssRegexWSub = re.compile(patternWSub, flags=re.IGNORECASE)
        self.plssReplaceWSub = '\\g<sub> ' + self.plssReplace



    """
        Sets the output folder.
    """
    def setOutputFolder(self, outputFolder):
        self.outputFolder = outputFolder

    def read_inputJson(self, input_json):
        js = open(input_json)
        ij = json.load(js)
        return ij

    def set_seuil(self, s):
        self.seuil = s

    """
            Returns the original string - applies no change.
    """

    def _noChange(self, string):
        return string

    """
        Returns true if the two strings are equal. The first string must be the
        reference string.
    """

    def _exactMatch(self, string1, string2):
        return string1 == string2

    """
        Normalizes string using self.translationTable
        It is assumed that the correct translation table will be set before
        attempting to normalize the string.
    """
    def translateString(self, label, string):
        normalized = string
        # Call the other cleaning functions before
        if self.translationTables.get(label):
            parts = string.split()
            for i in range(len(parts)):
                if parts[i]:
                    if parts[i][-1] == '.':
                        translated = self.translationTables.get(label).get(parts[i][:-1].lower(), parts[i])
                    elif parts[i][-1] in [',', ';', ')', ']']:
                        translated = self.translationTables.get(label).get(parts[i][:-1].lower(), parts[i][:-1]) + \
                                     parts[i][-1]
                    else:
                        translated = self.translationTables.get(label).get(parts[i].lower(), parts[i])
                    if parts[i] != translated:
                        parts[i] = translated
            normalized = ' '.join(parts)
        return normalized

    def _getSortedAttrsForLabel(self, label):
        # sortedAttrs = []
        # if label.versions:
        #     for version in label.versions:
        #         for i in range(version["votes"]):

        # Normalize any default responses
        sortedAttrsTemp = {}
        if label.versions:
            for version in label.versions:
                if version["data"].get("value"):  # TODO original emigrant json has more than one items, which maybe not exist in our case
                    normalized = self.clean(version["data"]["value"])
                    # Apply all lossless functions for this attribute
                    if self.useFunctionNormalizer and False:  # - TODO
                        losslessFuncs = self.labelMap[label].funcs
                        for func in losslessFuncs:
                            normalized = getattr(self, func)(normalized)

                    # Apply all lossless translation tables for this attribute
                    if self.useTranslationNormalizer:
                        normalized = self.translateString(label, normalized)
                    # if attr[key] != normalized and (self.useFunctionNormalizer or self.useTranslationNormalizer):
                    # if version["data"] != normalized or (self.useFunctionNormalizer or self.useTranslationNormalizer):
                    #     self.normalizedFileWriter.writerow(["orig:", version["data"]["value"]])
                    #     self.normalizedFileWriter.writerow(["norm:", normalized])
                    #     self.normalizedFile.flush()

                    # Using the cleaned version of the data
                    sortedAttrsTemp[version["data"]["value"]] = normalized

        # Copy back the normalized version
        sortedAttrs = sortedAttrsTemp
        # Sort attributes in order of descending length
        # sortedAttrs = sorted(sortedAttrsTemp, key=len, reverse=True)
        label.normalized_versions = sortedAttrs
        # Create a copy of the original attributes to use when determining
        # whether to add more or less workers to a task. Each attribute
        # will also be match with is corresponding original indice in attrSets
        indices = range(len(sortedAttrs))
        sortedAttrsCopy = sortedAttrs
        sortedAttrsCopy = zip(sortedAttrsCopy, indices)

        return sortedAttrsCopy

    """
        List of grouped words and their cumulative frequencies. In the
        end, the group with the largest cumulative frequency will have
        the majority selected from it. The idea is that only similar
        words will be located in the same group.
        group.total = cumulative weight of this group
        group.aggMap = dictionary of key to weight

        If useLossyNormalizers = True, then lossy normalizers will be used as
        well in the comparision. Else, only lossless normalizers will be used.
    """
    def _buildFrequencyList(self, label, useLossyNormalizers):
        freqList = []
        # Loop over each attribute to try to put it in a group
        for original, normalized in label.normalized_versions.items():
            attrFound = False
            # Look over all groups 第一次循环没有freqlist为空，所以直接添加第一个attr
            for group in freqList:
                for key in group.aggMap.keys():
                    # Insert exactly
                    if self.comparator(key, normalized):
                        for version in label.versions:
                            if version["data"].get("value"):
                                if version["data"]["value"] == original:
                                    group.aggMap[key] += version["votes"]
                                    group.total += version["votes"]
                                    attrFound = True
                                    break
                        break
                    # Try approximate match needed
                    if useLossyNormalizers:
                        s1 = self.lossyClean(key)
                        s2 = self.lossyClean(normalized)
                        if self.approx(s1, s2) or self.comparator(s1, s2):
                            for version in label.versions:
                                if version["data"]["value"] == original:
                                    group.aggMap[normalized] += version["votes"]
                                    group.aggMap[key] += version["votes"]
                                    group.total += version["votes"]
                                    attrFound = True
                                    break
                            break
                if attrFound:
                    break
            # If no exact or approximate matches, create a new entry
            if not attrFound:
                newEntry = AggMap()
                for version in label.versions:
                    if version["data"].get("value"):
                        if version["data"]["value"] == original:
                            newEntry.aggMap[normalized] += version["votes"]
                            newEntry.total += version["votes"]
                freqList.append(newEntry)
        return freqList

    """
        Returns the majority entry(ies), the votes for the entry(ies), and all
        the keys that were in the majority group containing that entry. The
        keys that were in the majority group containing the majority entry
        essentially 'voted' for the majority entry.
    """
    def _majorityFromFrequencyList(self, freqList):
        # Search for the majority entry
        maxVotes_entry = -1
        maxVotes_group = -1
        majorGroup = []
        # Find the majority group(s)
        for group in freqList:
            if group.total == maxVotes_entry:
                maxVotes_group = maxVotes_entry
                majorGroup.append(group.aggMap)
            elif group.total > maxVotes_entry:
                majorGroup = [group.aggMap]
                maxVotes_group = maxVotes_entry
                maxVotes_entry = group.total

        # freqList.sort(key=lambda group : group.total, reverse=True)

        # Search for the majority value in the majority group
        # Assumption is the similar entries in the same group are
        # mispellings, but their vote counts towards the biggest entry
        currMax = -1
        majorEntry = []
        for group in majorGroup:
            # unsortKeys = group.keys()
            # unsortKeys.sort(key=lambda s: -len(s))
            unsortKeys = sorted(group, key=lambda s: -len(s))
            for key in unsortKeys:
                if group[key] == currMax:
                    majorEntry.append(key)
                elif group[key] > currMax:
                    majorEntry = [key]
                    currMax = group[key]

        # All entries that were in the majority entry. Usually only one,
        # but can be multiple if a consensus was not reached
        majorGroupKey = []
        for group in majorGroup:
            for key in group.keys():
                majorGroupKey.append(key)
        return majorEntry, maxVotes_entry, maxVotes_group, majorGroupKey

    """
        Helper method to flatten a list of AggMaps.
        Returns a list in the following format:
        [[Aggmap1's k,v], [Aggmap2's k,v], ... ]
    """
    def _flattenAggMapList(self, l):
        ret = []
        # Traverse of AggMaps
        for m in l:
            t = []
            # Traverse over key's and values in that AggMap
            for k, v in m.aggMap.items():
                t.append((k, v))
            ret.append(t)
        return ret

    def get_labels_by_page(self):
        labels_by_page = []
        for subject in self.input_json["subjects"]:
            sb = {"id": subject["id"], "superID": subject["superID"], "assertions": []}
            for assertion in subject["assertions"]:
                # labels.append(assertion["name"])
                l = Label(assertion)
                # self.output_pages.append(sb)
                sb["assertions"].append(l)
            labels_by_page.append(sb)
        return labels_by_page

    # def getKeyLabel(self):
    #     kl = []
    #     for subject in self.inputJson["subjects"]:
    #         kl.append(subject["id"])
    #     return kl
    #
    # """
    #     Returns the grouping file header.
    # """
    # def getGroupingHeader(self):
    #     row = [self.keyLabel]
    #     for label in self.labels:
    #         row.append(label)
    #     return row
    #
    # """
    #     Returns the consensus file header.
    # """
    # def getConsensusHeader(self):
    #     row = [self.keyLabel]
    #     for label in self.labels:
    #         row.append(label)
    #     return row
    #
    # """
    #     Returns the majority file header.
    # """
    # def getMajorHeader(self):
    #     row = [self.keyLabel]
    #     for label in self.labels:
    #         row.append(label)
    #         # Options for the label's consensus
    #         row.append('Options')
    #         # The max vote for workers within the label
    #         row.append('Max')
    #         # The total number of votes
    #         row.append('Out of')
    #         # Max / Total
    #         row.append('Ratio')
    #         # 'ok' if the label reached a majority
    #         row.append('Majority')
    #         # Lossy or lossless
    #         row.append('Algorithm Type')
    #         # Consensus response type (real / blank) if consensus is reached
    #         row.append('Consensus Response Type')
    #     # 'ok' if all the labels for the task reached consensus
    #     row.append("Complete Consensus")
    #     return row

    def getConsensus(self, page):
        consensus_count = 0
        labels_count = 0
        # Iterate over the labels to to find a consensus per label
        for label in page["assertions"]:

            # Indicates if lossy normalizer is used for a particular label
            useLossyNormalizers = False
            # Indicates if consensus is reached for a particular label
            consensusFound = False

            # Get the sorted attributes for this label from the original
            # attribute set
            sortedAttrsCopy = self._getSortedAttrsForLabel(label)

            # Two iterations to find consensus: the first without the lossy
            # normalizers and the second with the lossy normalizers. All labels
            # will go through the first iteration, but only those that do not reach
            # consensus in the first iteration will move to the second iteration.
            for consensusIteration in range(1):
                # Break early if we found a consensus the first found (using
                # lossless normalizers)
                if consensusFound:
                    break

                # Use lossy normalizers during the second iteration
                if consensusIteration == 1:
                    useLossyNormalizers = True

                # List of grouped words and their cumulative frequencies. In the
                # end, the group with the largest cumulative frequency will have
                # the majority selected from it. The idea is that only similar
                # words will be located in the same group.
                # group.total = cumulative weight of this group
                # group.aggMap = dictionary of key to weight
                freqList = self._buildFrequencyList(label, useLossyNormalizers)

                # Get the majority entry(ies), the votes for that entry(ies),
                # as well the entries that voted for the majority entry(ies).
                majorEntry, maxVotes_entry, maxVotes_group, majorGroupKey = self._majorityFromFrequencyList(freqList)
                totalVotes = label.totalvotes()

                # # The entries not in the majority group
                # ignoredEntries = set(indice for value, indice in
                #                      sortedAttrsCopy if value not in
                #                      majorGroupKey)
                # # The entries in the majority group
                # usedEntries = set(indice for value, indice in
                #                   sortedAttrsCopy if value in
                #                   majorGroupKey)
                #
                votesForMajority = floor(0.5 * totalVotes) + 1

                if totalVotes > self.min_votes:  # - TODO original: 1
                    # It only makes sense to calsulate ratio if there is more
                    # than 1 worker's answer
                    if self.top2:
                        if (maxVotes_group != -1):
                            ratio = maxVotes_entry / float(maxVotes_entry + maxVotes_group)
                        else:
                            ratio = 1
                    else:
                        ratio = maxVotes_entry / float(totalVotes)
                else:
                    ratio = 0

                # A label that reached majority will be processed here only.
                if ratio > self.seuil:
                    consensusFound = True
                    label.status = "complete"
                    label.data["value"] = majorEntry[0]  # TODO by default, the first one
                    consensus_count += 1
            # somme labels don't have anything, or have multiple values in "data" which should be ignore
            if label.data is not None:
                if label.data.get("value"):
                    labels_count += 1
                # Format grouping row
                # groupingRow.append(self._flattenAggMapList(freqList))

                # Algorithm type
                # if useLossyNormalizers:
                #     majorityRow.append('lossy')
                # else:
                #     majorityRow.append('lossless')
                # Consensus Response Type
                # Real
                # if len(majorEntry) == 1 and majorEntry[0] != self.defaultResponse:
                #     majorityRow.append('real')
                # # Blank / Default response
                # elif len(majorEntry) == 1 and majorEntry[0] == self.defaultResponse:
                #     majorityRow.append('blank')
                # More than one majority response
                # else:
                #     if self.defaultResponse in majorEntry:
                #         # This really should not happen
                #         majorityRow.append('blank2')
                #     else:
                #         majorityRow.append('real')
                #     self._writeDiffToFile(fileKey, label, freqList)

                # totalOk += 1
                # votesExtra = maxVotes - votesForMajority
                # # Calculate the min number of votes that can be removed from
                # # the majority and still allow the majority to be kept
                # minVotesNeededToKeepMajority = min(
                #     minVotesNeededToKeepMajority, votesExtra)
                # # Update the set of entries used for calculating a majority to
                # # be the intersection of entries that have been used so far and
                # # the set of entries that were were to calculate the majority
                # # for this attribute
                # entriesUsedForMajority &= usedEntries
            # Only process labels that did not reach a majority if we are
            # in the consensus iteration using lossy normalizers.
            # In other words, anything here did not reach a consensus!
            # elif useLossyNormalizers:
            #     # Format grouping row
            #     groupingRow.append(self._flattenAggMapList(freqList))
            #
            #     # Format consensus row
            #     if self.acceptBestWork:
            #         # Output best choice even when majority was not reached
            #         consensusRow.append(majorEntry[0])
            #     else:
            #         consensusRow.append('')
            #
            #     # Output the key diffs if this label did not reach a consensus
            #     self._writeDiffToFile(fileKey, label, freqList)
            #
            #     # How many votes are still needed for a majority?
            #     votesNeeded = votesForMajority - maxVotes_entry
            #     # If there are 2+ major entries, then we might need more
            #     # workers for this task
            #     if len(majorEntry) == 1:
            #         # Calculate the max number of votes needed for all
            #         # attributes to attain the majority
            #         maxVotesNeededForMajority = max(votesNeeded,
            #                                         maxVotesNeededForMajority)
            #         # Update the set of ignored entries to be the intersection
            #         # of the set of entries that have been ignored so far and
            #         # the set of entries that were ignored when calculating the
            #         # consensus for this attribute
            #         # entriesNotUsedForMajority &= ignoredEntries
            #     # This ensures that the task will be assigned more workers
            #     else:
            #         maxVotesNeededForMajority = len(attrSets)
        return consensus_count, labels_count


        # Before returning, create the worker need row if this task did not reach a
        # satisfactory consensus when considering all fields.
        # Satisfactory consensus: All labels must reach consensus, there must
        # be a least 2 workers for this task

        # Entries that can be removed and still keep the consensus
        # entriesThatCanBeRemoved = entriesUsedForMajority & entriesNotUsedForMajority
        #
        # # The task did not reach complete consensus
        # if totalOk != len(self.labels) or len(attrSets) == 1:
        #     majorityRow.append('')
        #     workerNeedRow = [fileKey]
        #     workerNeedRow.append(totalOk)
        #     # Only one worker for this task
        #     if len(attrSets) == 1:
        #         workerNeedRow.append('More')
        #         workerNeedRow.append('Only 1 worker assigned to task')
        #     # Should not take away a worker if there are only two workers
        #     elif len(attrSets) == 2:
        #         workerNeedRow.append('More')
        #         workerNeedRow.append('Need one more worker for consensus')
        #     # If the max votes needed for a group to reach a complete majority
        #     # and the max votes is also less than the number of allowable
        #     # entries to remove, then entries can removed to allow the task to
        #     # achieve complete consensus
        #     elif maxVotesNeededForMajority <= minVotesNeededToKeepMajority and maxVotesNeededForMajority <= len(
        #             entriesThatCanBeRemoved):
        #         reason = 'Can remove ' + str(int(maxVotesNeededForMajority))
        #         reason += ' worker(s) (' + str(len(attrSets))
        #         reason += ' total) from ('
        #         for i in entriesThatCanBeRemoved:
        #             reason += str(i) + ' '
        #         reason += ') to reach full consensus'
        #         workerNeedRow.append('Less')
        #         workerNeedRow.append(reason)
        #     # By default assign more workers to a task
        #     else:
        #         workerNeedRow.append('More')
        #         workerNeedRow.append('Default')
        # # The task did reach complete consensus
        # else:
        #     majorityRow.append('ok')

        # return majorityRow, groupingRow, consensusRow  # , workerNeedRow

    """
        Reads the input file, computes the grouping and majority, and writes the
        results to the output files.
        Should be called after setting any optional parameters for the
        ConsensusCalculator.
    """
    def calculateConsensus(self):
        # Set up input file reader

        # csvInputFileReader = csv.DictReader(csvInputFile, dialect='excel')

        if not self.outputFolder:
            self.outputFolder = os.path.dirname(self.inputJson)
        if not os.path.exists(self.outputFolder):
            os.makedirs(self.outputFolder)

        print("Creating file attribute map...")

        # Create the file attribute map
        # Maps filenames to the rows associated with them
        # fileMap = collections.defaultdict(list)
        # Each row is a dictionary of strings to strings
        # Keys are the names of the columns (skipped by the reader)
        # Values are data from the row being read
        #for row in csvInputFileReader:
        #    fileMap[row[self.keyLabel]].append(row)
        # for index, subject in enumerate(self.inputJson["subjects"]):
        #     # if index % 10 == 0:
        #     #     print("did "+str(index)+" pages")  # not right
        #     for assertion in subject["assertions"]:
        #         fileMap[subject["id"]].append(assertion)

        print("Determining consensus among data...")
        # Create and write consensus data
        # Data written to output is not sorted by keyLabel
        numPagesProcessed = 0
        total_page = len(self.labels_by_page)
        total_consensus = 0
        total_label = 0
        startTime = time.time()

        with open(os.path.join(self.outputFolder, 'ConsensusCount.txt'), 'w') as output:
            for page in self.labels_by_page:  # for key in sorted(output_json["subjects"]):  #
                consensus_count, labels_count = self.getConsensus(page)
                total_consensus += consensus_count
                total_label += labels_count
                page["assertions"] = [label.to_json() for label in page["assertions"]]
                numPagesProcessed += 1
                # Print some output for calculations that take a long time
                if numPagesProcessed % 1000 == 0:
                    print("Completed", numPagesProcessed, "out of", total_page, "pages")
                output.write(str(consensus_count) + " / " + str(len(page["assertions"])) + "\n")
                output.flush()
        stopTime = time.time()
        print("Total times:", stopTime - startTime)
        # print("output to json...")
        # file_to_write = open(os.path.join(self.outputFolder, 'result.json'), 'w')
        # json.dump({"subjects": self.labels_by_page}, file_to_write)
        # file_to_write.close()
        return total_consensus * 1.0 / total_label

    def shuffle(self, label):
        list_normalized = sorted(label.group_dicts().items(), key=lambda x: x[1][0], reversed=True)
        if list_normalized[0][1][0] >= self.min_votes:
            print("Reached consensus if the majorities are at the first place with ratio = 100%")
        elif list_normalized[0][1][0] *1.0 / self.min_votes >= self.seuil:
            print("Reached consensus if the majorities are at the first place with ratio >= seuil")
        else:
            print("Consensus not found")


def plot(axes_x, axes_y):
    sns.set_style(style="ticks")
    x = np.array(axes_x)
    y = np.array(axes_y)
    plt.plot(x, y)
    plt.xlabel("ratio")
    plt.ylabel("consensus%")
    plt.show()


def find_seuil(start, end, scan):
    percentage_consensus = []
    seuil = []
    for s in np.arange(start, end, scan):
        getConsensus = Consensus('dataset.json')
        getConsensus.setOutputFolder('resTotal_' + str(s))
        getConsensus.set_seuil(s)
        pc = getConsensus.calculateConsensus()
        percentage_consensus.append(pc)
        seuil.append(s)
    plot(seuil, percentage_consensus)


# Combine json files in a directory into one single json file
def combine_json(dit):
    print('start...')
    i = 0
    json_collection = {}
    for element in os.listdir(dit):
        i += 1
        if element.endswith('.json'):
            # print("'%s' est un fichier texte" % element)
            # print('emigrant/'+str(element))
            #
            js = open(dit+str(element), encoding='utf-8')
            ij = json.load(js)
            for page in ij["subjects"]:
                page["superID"] = str(element)
                json_collection.setdefault("subjects", []).append(page)
    file_to_write = open('dataset.json', 'w')
    json.dump(json_collection, file_to_write)
    file_to_write.close()
    print('ok')


def main():
    combine_json("emigrant/")
    # getConsensus = Consensus('dataset.json')
    # getConsensus.setOutputFolder('resTotal')
    # getConsensus.calculateConsensus()
    #
    find_seuil(0.8, 1.1, .05)


if __name__ == "__main__":
    main()

