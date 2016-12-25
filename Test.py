# test codes
import json
from difflib import ndiff
from math import floor
import argparse
import csv
import collections
import os
import re
import time

# f = open('emigrant/5637a1a03262330003ce1c00.json')

# print(jso)


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
    def __init__(self, inputFile):
        # Indicates if output is verbose for debugging
        self.debug = False

        # Input csv file
        self.inputJson = self.readInputJson(inputFile)
        # Label that consensus entries are grouped by
        self.keyLabel = self.getKeyLabel()
        # Output folder
        self.outputFolder = None
        # Indicates if lossless custom functions are to be used for normalizing data
        self.useFunctionNormalizer = False
        # Indicates if lossless translation tables are to be used for normalizing data
        self.useTranslationNormalizer = False
        # Indicates if voting is done as (top group/total entries) "False" or
        #                                (top group > second top group) "True"
        self.top2 = False
        # Indicates that all possible number of worker should be tried to
        # find the minimum number of workers needed for full consistency
        self.getMinWorker = False
        # Indicates if the work from a single worker should be output to the
        # consensus file.
        self.acceptBestWork = False

        # Maps the labels to the translation tables and dictionaries they will
        # need
        self.labelMap = None
        # Labels to find a consensus for
        # self.labels = labelMap.keys()
        self.labels = self.getLabels()

        # Output file names - TODO allow configuration?
        # File that shows the grouping of words
        self.groupingFileName = 'Grouping.csv'
        # Shows which value was chosen if a consensus was reached
        self.majorityFileName = 'Majority.csv'
        # Final consensus response achieved
        self.consensusFileName = 'Consensus.csv'
        # Shows which tasks did not achieve consensus when considering all the
        # fields in the row. Also determines if that tasks could have achieved
        # consensus with more or less workers.
        self.workerNeedFileName = 'WorkerNeed.csv'
        # Stores all changes performed to the original data by lossless transformations
        self.normalizedFileName = 'Normalized.csv'
        self.normalizedFile = None
        self.normalizedFileWriter = None

        # Diff output file name
        self.diffOutputFileName = 'Diff.txt'

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

    def readInputJson(self, input_json):
        js = open(input_json)
        ij = json.load(js)
        print('*********************')
        for page in ij["subjects"]:
            for assertion in page["assertions"]:
                print(assertion["data"])
        print('*********************')
        return ij

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

    def _getSortedAttrsForLabel(self, attrSets, label):
        sortedAttrs = []
        for attrset in attrSets:
            if attrset["name"] == label:
                if attrset["versions"]:
                    for version in attrset["versions"]:  # 找到该label对应的所有值
                        for i in range(version["votes"]):
                            sortedAttrs.append(version["data"])
            # sortedAttrs = [attrSet[label] for attrSet in attrset["versions"]]
        print(sortedAttrs)
        # Normalize any default responses
        sortedAttrsTemp = []
        for attr in sortedAttrs:
            for key in attr:
                normalized = self.clean(attr[key])
                # Apply all lossless functions for this attribute
                if self.useFunctionNormalizer and False:  # - TODO
                    losslessFuncs = self.labelMap[label].funcs
                    for func in losslessFuncs:
                        normalized = getattr(self, func)(normalized)

                # Apply all lossless translation tables for this attribute
                if self.useTranslationNormalizer:
                    normalized = self.translateString(label, normalized)
            # if attr[key] != normalized and (self.useFunctionNormalizer or self.useTranslationNormalizer):
            if attr[key] != normalized or (self.useFunctionNormalizer or self.useTranslationNormalizer):
                self.normalizedFileWriter.writerow(["orig:" + key, attr[key]])
                self.normalizedFileWriter.writerow(["norm:", normalized])
                self.normalizedFile.flush()

            # Using the cleaned version of the data
            sortedAttrsTemp.append(normalized)

        # Copy back the normalized version
        sortedAttrs = sortedAttrsTemp
        # Sort attributes in order of descending length
        sortedAttrs.sort(key=len, reverse=True)

        # Create a copy of the original attributes to use when determining
        # whether to add more or less workers to a task. Each attribute
        # will also be match with is corresponding original indice in attrSets
        indices = range(len(sortedAttrs))
        sortedAttrsCopy = sortedAttrs[:]
        sortedAttrsCopy = zip(sortedAttrsCopy, indices)

        return sortedAttrs, sortedAttrsCopy

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
    def _buildFrequencyList(self, sortedAttrs, useLossyNormalizers):
        freqList = []
        # Loop over each attribute to try to put it in a group
        for sortedAttr in sortedAttrs:
            attrFound = False
            # Look over all groups 第一次循环没有freqlist为空，所以直接添加第一个attr
            for group in freqList:
                for key in group.aggMap.keys():
                    # Insert exactly
                    if self.comparator(key, sortedAttr):
                        group.aggMap[key] += 1
                        group.total += 1
                        attrFound = True
                        break
                    # Try approximate match needed
                    if useLossyNormalizers:
                        s1 = self.lossyClean(key)
                        s2 = self.lossyClean(sortedAttr)
                        if (self.approx(s1, s2) or self.comparator(s1, s2)):
                            group.aggMap[sortedAttr] += 1
                            group.aggMap[key] += 1
                            group.total += 1
                            attrFound = True
                            break
                if attrFound:
                    break
            # If no exact or approximate matches, create a new entry
            if not attrFound:
                newEntry = AggMap()
                newEntry.aggMap[sortedAttr] += 1
                newEntry.total += 1
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
        maxVotes = -1
        maxVotes2 = -1
        majorGroup = []
        # Find the majority group(s)
        for group in freqList:
            if (group.total == maxVotes):
                maxVotes2 = maxVotes
                majorGroup.append(group.aggMap)
            elif (group.total > maxVotes):
                majorGroup = [group.aggMap]
                maxVotes2 = maxVotes
                maxVotes = group.total
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
        return majorEntry, maxVotes, maxVotes2, majorGroupKey

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

    def getLabels(self):
        labels = []
        for subject in self.inputJson["subjects"]:
            for assertion in subject["assertions"]:
                labels.append(assertion["name"])
        return labels

    def getKeyLabel(self):
        kl = []
        for subject in self.inputJson["subjects"]:
            kl.append(subject["id"])
        return kl

    """
        Returns the grouping file header.
    """
    def getGroupingHeader(self):
        row = [self.keyLabel]
        for label in self.labels:
            row.append(label)
        return row

    """
        Returns the consensus file header.
    """
    def getConsensusHeader(self):
        row = [self.keyLabel]
        for label in self.labels:
            row.append(label)
        return row

    """
        Returns the majority file header.
    """
    def getMajorHeader(self):
        row = [self.keyLabel]
        for label in self.labels:
            row.append(label)
            # Options for the label's consensus
            row.append('Options')
            # The max vote for workers within the label
            row.append('Max')
            # The total number of votes
            row.append('Out of')
            # Max / Total
            row.append('Ratio')
            # 'ok' if the label reached a majority
            row.append('Majority')
            # Lossy or lossless
            row.append('Algorithm Type')
            # Consensus response type (real / blank) if consensus is reached
            row.append('Consensus Response Type')
        # 'ok' if all the labels for the task reached consensus
        row.append("Complete Consensus")
        return row

    def getConsensus(self, fileKey, attrSets):
        # The majority statistics, grouping, and consensus rows to be returned
        majorityRow = [fileKey]
        groupingRow = [fileKey]
        consensusRow = [fileKey]
        # The worker need row to be returned
        workerNeedRow = None

        # For the workerNeedRow
        # The total number of labels that have achieved consensus
        totalOk = 0
        # The set of entries that can be ignored (removed from the input) and
        # have this task still reach an overall consensus
        entriesNotUsedForMajority = set(i for i in range(len(attrSets)))
        # The max number of votes a label is lacking to achieve consensus
        # (ex if 4 votes were received and 7 were needed,
        # maxVotesNeededForMajority = max(3, maxVotesNeededForMajority)
        maxVotesNeededForMajority = 0
        # This represents the set of tasks that all entries had in common that
        # contributed to the majority. A subset of the intersection of
        # entriesUsedForMajority and entriesNotUsedForMajority that is at most
        # size minVotesNeededToKeepMajority can be removed for the tasks
        # without affecting the results
        entriesUsedForMajority = set(i for i in range(len(attrSets)))
        # This number represents the smallest number of votes a label had above
        # the majority
        minVotesNeededToKeepMajority = len(attrSets)
        # Iterate over the labels to to find a consensus per label
        for label in self.labels:
            # Indicates if lossy normalizer is used for a particular label
            useLossyNormalizers = False
            # Indicates if consensus is reached for a particular label
            consensusFound = False

            # Get the sorted attributes for this label from the original
            # attribute set
            sortedAttrs, sortedAttrsCopy = self._getSortedAttrsForLabel(attrSets, label)

            # Two iterations to find consensus: the first without the lossy
            # normalizers and the second with the lossy normalizers. All labels
            # will go through the first iteration, but only those that do not reach
            # consensus in the first iteration will move to the second iteration.
            for consensusIteration in range(2):
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
                freqList = self._buildFrequencyList(sortedAttrs, useLossyNormalizers)

                # Get the majority entry(ies), the votes for that entry(ies),
                # as well the entries that voted for the majority entry(ies).
                majorEntry, maxVotes, maxVotes2, majorGroupKey = self._majorityFromFrequencyList(freqList)
                totalVotes = len(sortedAttrs)

                # The entries not in the majority group
                ignoredEntries = set(indice for value, indice in
                                     sortedAttrsCopy if value not in
                                     majorGroupKey)
                # The entries in the majority group
                usedEntries = set(indice for value, indice in
                                  sortedAttrsCopy if value in
                                  majorGroupKey)

                votesForMajority = floor(0.5 * totalVotes) + 1

                if (totalVotes > 0):  # - TODO original: 1
                    # It only makes sense to calsulate ratio if there is more
                    # than 1 worker's answer
                    if self.top2:
                        if (maxVotes2 != -1):
                            ratio = maxVotes / float(maxVotes + maxVotes2)
                        else:
                            ratio = 1
                    else:
                        ratio = maxVotes / float(totalVotes)
                else:
                    ratio = 0

                # A label that reached majority will be processed here only.
                if ratio > 0.5:
                    consensusFound = True

                    # Format grouping row
                    groupingRow.append(self._flattenAggMapList(freqList))

                    # Format consensus row
                    consensusRow.append(majorEntry[0])

                    # Format this majority row - see self.getMajorHeader()
                    # Majority corresponding to label
                    majorityRow.append(majorEntry)
                    # Options
                    majorityRow.append(len(majorEntry))
                    # Max (max votes)
                    majorityRow.append(maxVotes)
                    # Out of
                    majorityRow.append(totalVotes)
                    # Ratio
                    majorityRow.append(ratio)
                    # Label Consensus
                    majorityRow.append('ok')
                    # Algorithm type
                    if useLossyNormalizers:
                        majorityRow.append('lossy')
                    else:
                        majorityRow.append('lossless')
                    # Consensus Response Type
                    # Real
                    if len(majorEntry) == 1 and majorEntry[0] != self.defaultResponse:
                        majorityRow.append('real')
                    # Blank / Default response
                    elif len(majorEntry) == 1 and majorEntry[0] == self.defaultResponse:
                        majorityRow.append('blank')
                    # More than one majority response
                    else:
                        if self.defaultResponse in majorEntry:
                            # This really should not happen
                            majorityRow.append('blank2')
                        else:
                            majorityRow.append('real')
                        self._writeDiffToFile(fileKey, label, freqList)

                    totalOk += 1
                    votesExtra = maxVotes - votesForMajority
                    # Calculate the min number of votes that can be removed from
                    # the majority and still allow the majority to be kept
                    minVotesNeededToKeepMajority = min(
                        minVotesNeededToKeepMajority, votesExtra)
                    # Update the set of entries used for calculating a majority to
                    # be the intersection of entries that have been used so far and
                    # the set of entries that were were to calculate the majority
                    # for this attribute
                    entriesUsedForMajority &= usedEntries
                # Only process labels that did not reach a majority if we are
                # in the consensus iteration using lossy normalizers.
                # In other words, anything here did not reach a consensus!
                elif useLossyNormalizers:
                    # Format grouping row
                    groupingRow.append(self._flattenAggMapList(freqList))

                    # Format consensus row
                    if self.acceptBestWork:
                        # Output best choice even when majority was not reached
                        consensusRow.append(majorEntry[0])
                    else:
                        consensusRow.append('')

                    # Format this majority row - see self.getMajorHeader()
                    # Majority corresponding to label
                    majorityRow.append(majorEntry)
                    # Options
                    majorityRow.append(len(majorEntry))
                    # Max (max votes)
                    majorityRow.append(maxVotes)
                    # Out of
                    majorityRow.append(totalVotes)
                    # Ratio
                    majorityRow.append(ratio)
                    # Label Consensus
                    majorityRow.append('')
                    # Algorithm Type
                    majorityRow.append('')
                    # Consensus Response Type, empty since majority was not reached
                    majorityRow.append('')

                    # Output the key diffs if this label did not reach a consensus
                    self._writeDiffToFile(fileKey, label, freqList)

                    # How many votes are still needed for a majority?
                    votesNeeded = votesForMajority - maxVotes
                    # If there are 2+ major entries, then we might need more
                    # workers for this task
                    if len(majorEntry) == 1:
                        # Calculate the max number of votes needed for all
                        # attributes to attain the majority
                        maxVotesNeededForMajority = max(votesNeeded,
                                                        maxVotesNeededForMajority)
                        # Update the set of ignored entries to be the intersection
                        # of the set of entries that have been ignored so far and
                        # the set of entries that were ignored when calculating the
                        # consensus for this attribute
                        entriesNotUsedForMajority &= ignoredEntries
                    # This ensures that the task will be assigned more workers
                    else:
                        maxVotesNeededForMajority = len(attrSets)

        # Before returning, create the worker need row if this task did not reach a
        # satisfactory consensus when considering all fields.
        # Satisfactory consensus: All labels must reach consensus, there must
        # be a least 2 workers for this task

        # Entries that can be removed and still keep the consensus
        entriesThatCanBeRemoved = entriesUsedForMajority & entriesNotUsedForMajority

        # The task did not reach complete consensus
        if totalOk != len(self.labels) or len(attrSets) == 1:
            majorityRow.append('')
            workerNeedRow = [fileKey]
            workerNeedRow.append(totalOk)
            # Only one worker for this task
            if len(attrSets) == 1:
                workerNeedRow.append('More')
                workerNeedRow.append('Only 1 worker assigned to task')
            # Should not take away a worker if there are only two workers
            elif len(attrSets) == 2:
                workerNeedRow.append('More')
                workerNeedRow.append('Need one more worker for consensus')
            # If the max votes needed for a group to reach a complete majority
            # and the max votes is also less than the number of allowable
            # entries to remove, then entries can removed to allow the task to
            # achieve complete consensus
            elif maxVotesNeededForMajority <= minVotesNeededToKeepMajority and maxVotesNeededForMajority <= len(
                    entriesThatCanBeRemoved):
                reason = 'Can remove ' + str(int(maxVotesNeededForMajority))
                reason += ' worker(s) (' + str(len(attrSets))
                reason += ' total) from ('
                for i in entriesThatCanBeRemoved:
                    reason += str(i) + ' '
                reason += ') to reach full consensus'
                workerNeedRow.append('Less')
                workerNeedRow.append(reason)
            # By default assign more workers to a task
            else:
                workerNeedRow.append('More')
                workerNeedRow.append('Default')
        # The task did reach complete consensus
        else:
            majorityRow.append('ok')

        return majorityRow, groupingRow, consensusRow, workerNeedRow

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

        # Set up output files
        groupingFile = open(os.path.join(self.outputFolder, self.groupingFileName), 'w')
        groupingFileWriter = csv.writer(groupingFile, dialect='excel')
        majorityFile = open(os.path.join(self.outputFolder, self.majorityFileName), 'w')
        majorityFileWriter = csv.writer(majorityFile, dialect='excel')
        consensusFile = open(os.path.join(self.outputFolder, self.consensusFileName), 'w')
        consensusFileWriter = csv.writer(consensusFile, dialect='excel')
        self.normalizedFile = open(os.path.join(self.outputFolder, self.normalizedFileName), 'w')
        self.normalizedFileWriter = csv.writer(self.normalizedFile, dialect='excel')
        # Output for tasks that did not reach a majority considering all fields
        workerNeedFile = open(os.path.join(self.outputFolder, self.workerNeedFileName), 'w')
        workerNeedFileWriter = csv.writer(workerNeedFile, dialect='excel')

        print("Creating file attribute map...")

        # Create the file attribute map
        # Maps filenames to the rows associated with them
        fileMap = collections.defaultdict(list)
        # Each row is a dictionary of strings to strings
        # Keys are the names of the columns (skipped by the reader)
        # Values are data from the row being read
        #for row in csvInputFileReader:
        #    fileMap[row[self.keyLabel]].append(row)
        for subject in self.inputJson["subjects"]:
            for assertion in subject["assertions"]:
                fileMap[subject["id"]].append(assertion)

        # Write output file headers
        groupingFileWriter.writerow(self.getGroupingHeader())
        groupingFile.flush()
        majorityFileWriter.writerow(self.getMajorHeader())
        majorityFile.flush()
        consensusFileWriter.writerow(self.getConsensusHeader())
        consensusFile.flush()
        workerNeedFileWriter.writerow(['Total # of attributes ', str(len(self.labels))])
        workerNeedFileWriter.writerow(['Name', '# attributes reaching consensus', 'More/Less workers needed', 'Reason'])

        print("Determining consensus among data...")
        # Create and write consensus data
        # Data written to output is not sorted by keyLabel
        numRowsProcessed = 0
        totalWithoutFullConsensus = 0
        startTime = time.time()
        for key in sorted(fileMap.keys()):
            if self.getMinWorker:
                majorityRow = None
                minW = 0
                for i in range(1, len(fileMap[key]) + 1):
                    majorityRow, groupingRow, consensusRow, workerNeedRow = self.getConsensus(key, fileMap[key][:i])
                    minW = i
                    if (majorityRow[-1] == 'ok'):
                        break
                if majorityRow:
                    groupingRow.append('Worker reduceable from/to:')
                    groupingRow.append(len(fileMap[key]))
                    groupingRow.append(minW)
                else:
                    continue
            else:
                majorityRow, groupingRow, consensusRow, workerNeedRow = self.getConsensus(key, fileMap[key])
            numRowsProcessed += 1
            groupingFileWriter.writerow(groupingRow)
            groupingFile.flush()
            majorityFileWriter.writerow(majorityRow)
            majorityFile.flush()
            consensusFileWriter.writerow(consensusRow)
            consensusFile.flush()
            # Write the workerNeed row if necessary
            if workerNeedRow:
                totalWithoutFullConsensus += 1
                workerNeedFileWriter.writerow(workerNeedRow)
                workerNeedFile.flush()

            # Print some output for calculations that take a long time
            if (numRowsProcessed % 100 == 0):
                stopTime = time.time()
                print
                "Completed", numRowsProcessed, "out of", len(fileMap), \
                "in", stopTime - startTime, " secs"
                startTime = stopTime

        # Footer for the workerNeed file
        workerNeedFileWriter.writerow(
            ['% of tasks that did not reach a satisfactory consensus: ',
             str((100.0 * totalWithoutFullConsensus) / numRowsProcessed)])

        # Close files
        # csvInputFile.close()
        groupingFile.close()
        majorityFile.close()
        consensusFile.close()
        self.normalizedFile.close()
        workerNeedFile.close()

    """
        Writes the diffs of the freqList into a output file.
    """
    def _writeDiffToFile(self, fileKey, label, freqList):
        if not self.debug:
            return
        diffOutput = []
        # Output diff between entries
        diffOutput.append('========\n')
        diffOutput.append(label + ' (' + fileKey + '):\n')

        groups = []
        # Traverse the AggMaps
        # Extract the keys, but keep their grouping
        # Also output the grouping of the keys to the output file
        for groupMap in freqList:
            tempList = []
            diffOutput.append('(\n')
            for key in groupMap.aggMap.keys():
                tempList.append(key)
                diffOutput.append('\t' + key + '\n')
            diffOutput.append(')\n')
            groups.append(tempList)
        diffOutput.append('========\n')

        # Compare only keys in different groups to each other
        # First group
        for i in range(len(groups)):
            # Items in the first group
            for k in range(len(groups[i])):
                # Second group
                for j in range(len(groups) - i - 1):
                    # Items in the second group
                    for h in range(len(groups[i + j + 1])):
                        # Write lossless clean first
                        s1 = (self.clean((groups[i])[k]) + '\n').splitlines(1)
                        s2 = (self.clean((groups[i + j + 1])[h]) + '\n').splitlines(1)
                        diff = ndiff(s1, s2)
                        diffOutput.append('[LOSSLESS]\n')
                        diffOutput.append(''.join(diff))
                        # Then write lossy clean
                        s1 = (self.lossyClean(self.clean((groups[i])[k])) + '\n').splitlines(1)
                        s2 = (self.lossyClean(self.clean((groups[i + j + 1])[h])) + '\n').splitlines(1)
                        diff = ndiff(s1, s2)
                        diffOutput.append('[LOSSY]\n')
                        diffOutput.append(''.join(diff))
                        diffOutput.append('~~~\n')
        diffWriter = open(os.path.join(self.outputFolder, self.diffOutputFileName), 'a')
        diffWriter.writelines(diffOutput)
        diffWriter.close()


def main():
    getConsensus = Consensus('emigrant/5637a1a03262330003e01c00.json')
    getConsensus.setOutputFolder('Result10')
    getConsensus.calculateConsensus()

if __name__ == "__main__":
    main()

