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
import copy
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import difflib as df

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
        self.list_ratio = []
        self.workers = []

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
        count = 0
        labels_by_page = []
        for subject in self.input_json["subjects"]:
            sb = {"id": subject["id"], "superID": subject["superID"], "assertions": []}
            if subject["assertions"] is not None and len(subject["assertions"]) > 0:
                for assertion in subject["assertions"]:
                    if assertion is not None:
                        if assertion["versions"] and len(assertion["versions"]) > 1:
                            l = Label(assertion)
                            count += 1
                            sb["assertions"].append(l)
                            # if len(assertion["versions"]) == 3 and l.totalvotes() == 21 or l.totalvotes() == 22:
                            #     print()
                labels_by_page.append(sb)
        print(count)
        return labels_by_page

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
                # if label.id == '580dba0d61643900032cbb03':
                #     print()
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
                ratio = 0
                if totalVotes > 1:  # - TODO original: 1 // self.minVotes
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
                if ratio >= self.seuil:
                    if label.data is not None:
                        if label.data.get("value"):  # for test when seuil = 0
                            consensusFound = True
                            label.status = "completed"
                            label.data = majorEntry[0] if len(majorEntry) > 0 else None  # TODO by default, the first one
                            consensus_count += 1
            # somme labels don't have anything, or have multiple values in "data" which should be ignore
            if label.data is not None:
                if label.data.get("value"):
                    labels_count += 1
                    label.ratio = ratio
                    self.list_ratio.append(ratio)
            label.ratio = ratio
        # self.total_labels += labels_count
        return consensus_count, labels_count

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

        print("Determining consensus among data...")
        # Create and write consensus data
        # Data written to output is not sorted by keyLabel
        numPagesProcessed = 0
        total_page = len(self.labels_by_page)
        total_consensus = 0
        total_label = 0
        # ...
        outputJson = []
        startTime = time.time()
        with open(os.path.join(self.outputFolder, 'ConsensusCount.txt'), 'w') as output:
            for page in self.labels_by_page:  # for key in sorted(output_json["subjects"]):  #
                consensus_count, labels_count = self.getConsensus(page)
                total_consensus += consensus_count
                total_label += labels_count
                temp = copy.deepcopy(page)
                temp["assertions"] = [label.to_json() for label in page["assertions"]]
                outputJson.append(temp)
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
        # json.dump({"subjects": outputJson}, file_to_write)
        # file_to_write.close()
        return total_consensus * 1.0 / total_label

    def chronology(self):
        def auto_label(rects, ax, xticks):
            # Get y-axis height to calculate label position from.
            (y_bottom, y_top) = ax.get_ylim()
            y_height = y_top - y_bottom
            count = 0
            for rect in rects:
                if count in xticks:
                    # rect.set_color("#fa2a55")
                    height = rect.get_height()
                    label_position = height / y_height  # (y_height * 0.07)
                    ax.text(rect.get_x() + rect.get_width() / 2., label_position,
                            round(height, 2),
                            ha='center', va='bottom')
                count += 1

        list_ratio = []
        for page in self.labels_by_page:
            for label in page["assertions"]:
                versions = {}
                seq = label.votes_sequence()
                found = False
                for t in seq:
                    if versions.get(t):
                        versions[t] += 1
                    else:
                        versions.setdefault(t, 1)
                    if t == label.data["value"]:
                        lst = sorted(versions.items(), key=lambda x: x[1], reverse=True)
                        values = versions.values()
                        vl = 0
                        for v in values:
                            vl += v
                        if lst[0][0] == label.data["value"]:
                            ratio = lst[0][1] / float(vl)
                            if vl > 1:
                                if len(lst) > 1:
                                    if lst[1][1] / float(vl) >= ratio:
                                        continue
                                    else:
                                        list_ratio.append(ratio)  # consensus found
                                        found = True
                                        break
                                list_ratio.append(ratio)
                                found = True
                                break

                if not found and (label.data is not None) and label.data.get("value"):
                    list_ratio.append(label.ratio)

        def compare_chronology(l1, l2):

            # self.list_ratio
            l1.sort()
            print(len(l1))
            list_consensus1 = [1]
            cmp_consensus1 = []
            previous_r = l1[0]
            count = 1
            for i, v in enumerate(l1, start=1):
                if v == previous_r:
                    count += 1
                    continue
                else:
                    list_consensus1.append((len(l1) - i) / float(len(l1)))
                    cmp_consensus1.append(count)
                    previous_r = v
                    count = 1
            s1 = sorted(set(l1))

            # list_ratio
            l2.sort()
            list_consensus2 = [1]
            cmp_consensus2 = []
            previous_r2 = l2[0]
            count = 1
            for i, v in enumerate(l2, start=1):
                if v == previous_r2:
                    count += 1
                    continue
                else:
                    list_consensus2.append((len(l2) - i) / float(len(l2)))
                    cmp_consensus2.append(count)
                    previous_r2 = v
                    count = 1
            s2 = sorted(set(l2))


            xticks = []
            xlabels = []
            for i in range(1, len(list_consensus2)):
                if list_consensus2[i - 1] - list_consensus2[i] >= 0.03:
                    xticks.append(i - 1)
                    xlabels.append(s2[i - 1])

            colors = [c for c in sns.color_palette("Set1", 2)]
            fig, ax = plt.subplots()
            rects1 = ax.bar(range(len(s1)), list_consensus1, color=colors[0], alpha=0.5)
            rects2 = ax.bar(range(len(s2)), list_consensus2, color=colors[1], alpha=0.5)
            auto_label(rects2, ax, xticks)
            ax.set_xticks(xticks)
            ax.set_xticklabels([round(x, 2) for x in xlabels])
            ax.set_ylim(0, 1.1)
            ax.set_xlabel("ratio")
            ax.set_ylabel("%Consensus")
            diff = []
            dist = len(cmp_consensus1) - len(cmp_consensus2)
            print(cmp_consensus2, "\n", cmp_consensus1)
            for i in range(len(cmp_consensus2)):
                for k in range(len(cmp_consensus1)):
                    if s1[k] > s2[i]:
                        diff.append(sum(cmp_consensus2[:i]) - sum(cmp_consensus1[:k - 1]))
                        break
            diff = [round(d, 2) for d in diff]
            # if dist > 0:
            #     for i in range(len(cmp_consensus2)):
            #         diff.append(sum(cmp_consensus2[:i]) - sum(cmp_consensus1[0:i]))
            #     diff.extend([sum(cmp_consensus2) - sum(cmp_consensus1[:-dist + i]) for i in range(len(cmp_consensus1[-dist:]))])
            # else:
            #     for i in range(len(cmp_consensus1)):
            #         diff.append(sum(cmp_consensus2[:i]) - sum(cmp_consensus1[0:i]))
            #     diff.extend([sum(cmp_consensus2[:-dist + i]) - sum(cmp_consensus1) for i in range(len(cmp_consensus2[-dist:]))])
            # print(cmp_consensus1, "\n", cmp_consensus2, "\n", diff)
            ax2 = ax.twinx()
            line, = ax2.plot(range(len(diff)), diff, color="#feb308", label="Difference")
            ax2.set_ylabel("Diffrence of the count of consensus")

            # ax.set_ylim([0.2, 1.1])
            # plt.xlabel("Ratio")
            # plt.ylabel("%Consensus")
            plt.legend([rects1, rects2, line], ["Original", "Chronology", "Difference"])
            fig.tight_layout()
            plt.show()
        compare_chronology(self.list_ratio, list_ratio)

    def plot_seuil(self):
        def auto_label(rects, ax, xticks):
            # Get y-axis height to calculate label position from.
            (y_bottom, y_top) = ax.get_ylim()
            y_height = y_top - y_bottom
            count = 0
            for rect in rects:
                if count in xticks:
                    rect.set_color("#fa2a55")
                    height = rect.get_height()
                    label_position = height / y_height  # (y_height * 0.07)
                    ax.text(rect.get_x() + rect.get_width() / 2., label_position,
                            round(height, 2),
                            ha='center', va='bottom')
                count += 1
        self.list_ratio.sort()
        list_consensus = [1]
        previous_r = self.list_ratio[0]
        for i, v in enumerate(self.list_ratio, start=1):
            if v == previous_r:
                continue
            else:
                list_consensus.append((len(self.list_ratio) - i) / float(len(self.list_ratio)))
                previous_r = v
        s = sorted(set(self.list_ratio))
        xlabels = []
        xticks = []
        for i in range(1, len(list_consensus)):
            if list_consensus[i - 1] - list_consensus[i] >= 0.03:
                xticks.append(i - 1)
                xlabels.append(s[i - 1])
        print(xlabels)
        print(xticks)
        s = [round(d, 2) for d in s]
        fig, ax = plt.subplots()
        rects = ax.bar(range(len(s)), list_consensus)
        auto_label(rects, ax, xticks)
        ax.set_xticks(xticks)
        ax.set_xticklabels([round(x, 2) for x in xlabels])

        plt.xlabel("Ratio")
        plt.ylabel("%Consensus")
        plt.show()

    def plot_propositions(self):

        def auto_label(rects, ax, key_list, height_transform):
            # Get y-axis height to calculate label position from.
            (y_bottom, y_top) = ax.get_ylim()
            # y_height = 60000  # y_top - y_bottom
            count = 0
            for rect in rects:
                height = height_transform[count]
                label_position = height - 1000  # (y_height * 0.07)
                key_position = height + 100  # (y_height * 0.007)
                # print(y_height)
                if key_list is None:
                    ax.text(rect.get_x() + rect.get_width() / 2., key_position,
                            str(height),
                            ha='center', va='bottom')
                    count += 1
                    continue
                if count < 3 and label_position - (height - rect.get_height() + 400) > 400:
                    ax.text(rect.get_x() + rect.get_width() / 2., label_position,
                            '%d' % int(rect.get_height()),
                            ha='center', va='bottom')
                    if key_list[count] != "":
                        ax.text(rect.get_x() + rect.get_width() / 2., key_position,
                                key_list[count],
                                ha='center', va='bottom')
                count += 1

        # propostions: an array(#propo, list_of votes of labels)
        propostions = list()  # each item is an array of dict{vk: #vk}
        for page in self.labels_by_page:
            for label in page["assertions"]:
                if (label.versions is not None) and len(label.versions) > 1:  # calcule pas #proposition = 1
                    v = label.totalvotes()
                    l = len(label.versions)
                    if l > len(propostions) + 1:
                        for i in range(len(propostions), l):
                            propostions.append([])
                    propostions[l - 2].append(v)

        # p_votes: reduce votes for each proposition
        proposition_votes = []
        for p in propostions:
            previous = -1
            p_with_dicts = {}
            p.sort()
            for v in p:
                if v != previous:
                    p_with_dicts.setdefault(str(v), 1)
                    previous = v
                else:
                    p_with_dicts[str(previous)] += 1
            proposition_votes.append(p_with_dicts)

        proposition_votes = [sorted(p.items(), key=lambda d: d[1], reverse=True) for p in proposition_votes]
        # construct several lists. each list represent dicts of votes
        mx = 0  # max length of p
        for p in proposition_votes:
            if len(p) > 0:
                v = len(p)
                mx = v if v > mx else mx
        colors = [c for c in sns.color_palette("Set2", 10)]
        xrange = range(2, len(proposition_votes) + 2, 1)
        height_transform = [0 for i in xrange]
        fig, ax = sns.plt.subplots()
        for i in range(0, 3):
            v_list = []
            key_list = []
            for j in range(len(proposition_votes)):
                if i > len(proposition_votes[j]) - 1:
                    v_list.append(0)
                    key_list.append("")
                else:
                    item = proposition_votes[j][i]
                    v_list.append(item[1])
                    key_list.append(item[0])
            ax.set_xticks([x for x in xrange])
            rects = ax.bar(xrange, v_list, 0.5, bottom=height_transform, color=colors[i % 3])
            for k in range(len(v_list)):
                height_transform[k] += v_list[k]
            auto_label(rects, ax, key_list, height_transform)

            # last to print all tests
            v_list = []
            for p in proposition_votes:
                v = 0
                for item in p:
                    v += item[1]
                v_list.append(v)
            print("sum", sum(v_list))
            for k in range(len(v_list)):
                v_list[k] -= height_transform[k]
            rects = ax.bar(xrange, v_list, 0.5, bottom=height_transform, color=colors[3])
        auto_label(rects, ax, key_list=None, height_transform=[x + y for x, y in zip(v_list, height_transform)])

        # plt.yticks(range(0, max(height_transform) + 10, 500))
        sns.set_style("whitegrid")
        plt.xticks(xrange)
        plt.ylabel("#Test")
        plt.xlabel("#propositions")
        plt.show()

    def plot_proposition(self, seuil, plot_range):
        def auto_label(rects, ax, list_consensus, height_list):
            # Get y-axis height to calculate label position from.
            (y_bottom, y_top) = ax.get_ylim()
            # y_height = 60000  # y_top - y_bottom
            for i, rect in enumerate(rects):
                height = height_list[i]
                label_position = height + 1  # (y_height * 0.07)
                ax.text(rect.get_x() + rect.get_width() / 2., label_position,
                        str(list_consensus[i]) + "/" + str(height_list[i]),
                        ha='center', va='bottom', rotation="vertical")


        # propostions: an array(#propo, list_of votes of labels)
        propostions = list()  # each item is an array of dict{vk: #vk}
        for page in self.labels_by_page:
            for label in page["assertions"]:
                if (label.versions is not None) and len(label.versions) > 1:  # calcule pas #proposition = 1
                    v = label.totalvotes()
                    if label.data.get("value") is None:
                        continue
                    l = len(label.versions)
                    if l > len(propostions) + 1:
                        for i in range(len(propostions), l):
                            propostions.append([])
                    propostions[l - 2].append((v, label.ratio))

        # p_votes: reduce votes for each proposition
        proposition_votes = []
        for p in propostions:
            previous = -1
            p_with_dicts = {}
            p.sort()
            for v in p:
                if v[0] != previous:
                    p_with_dicts.setdefault(str(v[0]), [v[1]])
                    previous = v[0]
                else:
                    p_with_dicts[str(previous)].append(v[1])
            proposition_votes.append(p_with_dicts)

        # start to plot
        proposition_votes = [sorted(p.items(), key=lambda d: d[0]) for p in proposition_votes]
        colors = [c for c in sns.color_palette("Set2", 10)]
        fig, ax = plt.subplots(len(plot_range))

        for i in plot_range:
            p = proposition_votes[i]
            votes = [d[0] for d in p]
            values = [d[1] for d in p]  # list of ratio
            values1 = []
            values2 = []
            for lr in values:
                lr.sort()
                found = False
                for k in range(len(lr)):
                    if lr[k] >= seuil:
                        values1.append(len(lr) - k)
                        values2.append(k)
                        found = True
                        break
                if not found:
                    values1.append(0)
                    values2.append(len(lr))
            print(values1)
            print(values2)
            rects1 = ax[i].bar(votes, values1, color="#f4320c", label="aaaa")
            rects2 = ax[i].bar(votes, values2, bottom=values1, color=colors[i - plot_range[0]])
            ax[i].set_title("Proposotions " + str(i + 2))
            xlim = [int(d) for d in votes]
            ax[i].set_xticks(sorted(xlim))
            ax[i].set_xticklabels(sorted(xlim))
            ax[i].set_xlim(min(xlim), max(xlim) + 1)
            # ax[i, j].set_legend([rects1, rects2], ["Consensus found", "Not found"])
            auto_label(rects1, ax[i], values1, [v1 + v2 for v1, v2 in zip(values1, values2)])

        sns.set_style("whitegrid")
        plt.ylabel("#Test")
        plt.xlabel("#Votes")
        fig.tight_layout()
        plt.show()

    def get_workers_contributions(self):
        label_list = []
        majority_list = np.zeros
        worker_list = []
        workers_labels = []
        count = 0
        for page in self.labels_by_page:
            labels = page["assertions"]
            if len(labels) > 0:
                for label in labels:
                    if label.versions and (label.data is not None) and label.data.get("value"):
                        label_list.append(label.id)
                        for version in label.versions:
                            for instance in version["instances"]:
                                match = [x for x in worker_list if x == instance["user_id"]]
                                if len(match) > 0:  # user_id exists
                                    i = worker_list.index(match[0])
                                    workers_labels[i][count] = label.normalized_versions[version["data"]["value"]]
                                else:  #user_id not found
                                    workers_labels.append(np.zeros(self.total_labels))
                                    workers_labels[-1][count] = label.normalized_versions[version["data"]["value"]]
                                    worker_list.append(instance["user_id"])

                        count += 1
        return np.array(workers_labels), np.array(worker_list), np.array(label_list)

    def mv_results(self):
        y = []
        m = []


def plot(ax, axes_x, axes_y, color="blue"):
    x = np.array(axes_x)
    y = np.array(axes_y)
    ax.plot(x, y, color=color)
    plt.xlabel("ratio")
    plt.ylabel("consensus%")
    plt.show()


def find_seuil1(start, end, scan):
    percentage_consensus = []
    seuil = []
    for s in np.arange(start, end, scan):
        getConsensus = Consensus('dataset.json', 3)
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
            json_collection.setdefault("subjects", [])
            for page in ij["subjects"]:
                page["superID"] = str(element)
                json_collection["subjects"].append(page)
    file_to_write = open('dataset.json', 'w')
    json.dump(json_collection, file_to_write)
    file_to_write.close()
    print('ok')


def main():
    # combine_json("emigrant/")
    getConsensus = Consensus('dataset.json', 3)
    getConsensus.setOutputFolder('test_refine_seuil')
    getConsensus.calculateConsensus()
    # getConsensus.plot_seuil()
    # getConsensus.chronology()
    # getConsensus.plot_propositions()
    getConsensus.plot_proposition(0.75, range(5))
    # find_seuil1(0, 1.1, .1)


if __name__ == "__main__":
    main()

