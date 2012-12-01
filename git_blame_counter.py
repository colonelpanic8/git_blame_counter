# -*- coding: utf-8 -*-
import os
import re
import subprocess


class BlameCounter(object):

	DIVIDER = '------------------------------'

	def __init__(
		self,
		search_re='',
		filename_re='.*\.(?:py|tmpl)',
		directory_ignore_re=None
	):
		self.path_matcher = re.compile(search_re)
		self.filename_matcher = re.compile(filename_re)
		self.directory_ignore_matcher = re.compile(directory_ignore_re) \
			if directory_ignore_re else None
		self.commiter_matcher = re.compile('\((.*?)\s*[0-9]{4}')
		self.blame_line_count_map = {}

	def get_matching_files(self):
		for directory_path, directory_names, filenames in os.walk('.'):
			if self.directory_ignore_matcher:
				for directory_name in directory_names:
					if self.directory_ignore_matcher.search(directory_name):
						del directory_names[directory_names.index(directory_name)]
			if self.path_matcher.search(directory_path):
				for filename in filenames:
					if self.filename_matcher.match(filename):
						yield os.path.join(directory_path, filename)
			else:
				for filename in filenames:
					file_path = os.path.join(directory_path, filename)
					if self.path_matcher.search(file_path) and \
						self.filename_matcher.match(filename):
						yield file_path

	def git_blame_files(self, filenames):
		for filename in filenames:
			yield subprocess.Popen(
				['git', 'blame', filename],
				stdout=subprocess.PIPE
			).communicate()[0]

	def count_blame_lines_in_chunks(self, chunk_size):
		for file_count, blame_output in enumerate(
			self.git_blame_files(self.get_matching_files())
		):
			if file_count % chunk_size == 0:
				self.print_results(
					max_committers=30,
					min_blame_lines=400
				)
			self._count_blame_lines(blame_output)

	def count_blame_lines(self):
		for blame_output in self.git_blame_files(self.get_matching_files()):
			self._count_blame_lines(blame_output)

	def _count_blame_lines(self, blame_output):
		for line in blame_output.split('\n'):
			match = self.commiter_matcher.search(line)
			if match:
				committer = match.group(1)
				self.blame_line_count_map[
					committer
				] = self.blame_line_count_map.setdefault(committer, 0) + 1

	def print_results(self, max_committers=None, min_blame_lines=None):
		print self.DIVIDER
		for (rank, (committer, blame_lines)) in enumerate(
			sorted(
				self.blame_line_count_map.iteritems(),
				key=lambda x: x[1],
				reverse=True
			)
		):
			if rank is not None and rank == max_committers:
				return
			if min_blame_lines is None or blame_lines > min_blame_lines:
				print str(rank + 1), committer, ': ', blame_lines


if __name__ == '__main__':
	import ipdb; ipdb.set_trace()
	BlameCounter().count_blame_lines_in_chunks(25)
