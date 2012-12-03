#!/usr/local/bin/python
import optparse
import os
import re
import subprocess


def segment(iterable, segment_length):
	if segment_length is None:
		yield iterable
		raise StopIteration
	def yield_length():
		for _ in xrange(segment_length):
			yield iterable.next()
	while True:
		segment = list(yield_length())
		if not segment:
			raise StopIteration
		yield segment


def build_file_extension_re(file_extensions):
	return '.*\.(?:' + '|'.join(file_extensions) + ')'


class BlameCounter(object):

	DIVIDER = '------------------------------'
	commiter_matcher = re.compile('\((.*?)\s*[0-9]{4}')

	def __init__(
		self,
		search_re='',
		filename_re='.*\.(?:py|tmpl)',
		directory_ignore_re=None,
		chunk_size=None,
		committer=None
	):
		self.path_matcher = re.compile(search_re)
		self.filename_matcher = re.compile(filename_re)
		self.directory_ignore_matcher = re.compile(directory_ignore_re) \
			if directory_ignore_re else None
		self.chunk_size = chunk_size
		self.committer = committer
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
			if subprocess.call(
				['git ls-files %s --error-unmatch' % filename],
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
			):
				continue
			yield (filename, subprocess.Popen(
				['git', 'blame', filename],
				stdout=subprocess.PIPE
			).communicate()[0])

	def count_blame_lines(self):
		for blame_output_chunk in segment(
			self.git_blame_files(self.get_matching_files()),
			self.chunk_size
		):
			self._count_blame_lines(blame_output_chunk)
			if self.chunk_size:
				self.print_results(
					max_committers=50,
					min_blame_lines=None
				)

	def _count_blame_lines(self, blame_outputs):
		for _, blame_output in blame_outputs:
			if self.committer and not self.committer in blame_output:
				continue
			for line in blame_output.split('\n'):
				match = self.commiter_matcher.search(line)
				if match:
					committer = match.group(1)
					self.blame_line_count_map[
						committer
					] = self.blame_line_count_map.setdefault(committer, 0) + 1

	def files_touched_by_comitter(self):
		blame_count_by_file = {}
		committer_matcher = re.compile('\((%s)\s*[0-9]{4}' % self.committer)
		for filename, blame_output in self.git_blame_files(
			self.get_matching_files()
		):
			if self.committer in blame_output:
				count = 0
				for line in blame_output.split('\n'):
					match = committer_matcher.search(line)
					if match:
						count +=1
				blame_count_by_file[filename] = count
				print filename, count
		return blame_count_by_file

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
	parser = optparse.OptionParser()
	parser.add_option(
		'--search-re',
		dest='search_re',
		help='A regular expression to use when inspecting filepaths'
	)
	parser.add_option(
		'-x',
		action='append',
		dest='file_extensions',
		help=('Search for filenames with the given file extension. '
			  'Can be used multiple times.')
	)
	parser.add_option(
		'--chunk-size',
		dest='chunk_size',
		type=int,
		help='Print the rankings at intervals of CHUNK_SIZE files.'
	)
	parser.add_option(
		'--committer',
		dest='committer',
		help=('Count blame lines only in files where COMMITTER appears. '
			  'Overrides --chunk-size.')
	)

	(namespace, _) = parser.parse_args()

	blame_counter_build_kwargs = {
		'committer': namespace.committer,
		'chunk_size': namespace.chunk_size
	}
	if namespace.file_extensions:
		blame_counter_build_kwargs['filename_re'] = build_file_extension_re(
			namespace.file_extensions
		)
	if namespace.search_re:
		blame_counter_build_kwargs['search_re'] = namespace.search_re

	blame_counter = BlameCounter(**blame_counter_build_kwargs)
	blame_counter.count_blame_lines()
	blame_counter.print_results()
