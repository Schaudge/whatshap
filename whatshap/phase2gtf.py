#!/usr/bin/env python3
"""
Read phasing information from a VCF, print statistics and write out a GTF file
that describes the found blocks.

The GTF file can be loaded into IGV. Since a block of phased variants is not
necessarily contiguos, each block is modelled as a "gene" in the GTF file that
can have multiple "exons". Each exon marks a set of adjacent variants which all
could be phased. If there are nonadjacent variants that belong to the same
block, there will be multiple "exons" connected with an arrow (in IGV).
"""
"""
* Statistics are written to stderr (no. of blocks,
  average length of blocks, etc.)

TODO
* Only the first sample is considered.
* Only SNPs are considered (indels are treated as if they did not exist).
* Homozygous calls are also ignored.
* factor out common code of parse_hp_tags and parse_pipe_notation
"""
import logging
import sys
from collections import Counter
import vcf
from argparse import ArgumentParser

__author__ = 'Marcel Martin'

logger = logging.getLogger(__name__)

def frequency_median(frequencies):
	"""
	Given a dictionary of frequencies, return the median.
	If the total no. of values is odd, the left of both
	middle values is returned.
	"""
	m = 0  # partial sum
	middle = (1 + sum(frequencies.values())) // 2
	for length in sorted(frequencies):
		m += frequencies[length]
		if m >= middle:
			return length
	# never reached
	assert False


class GtfWriter:
	def __init__(self, path):
		self._file = open(path, 'w')

	def write(self, chromosome, start, stop, name):
		"""
		Write a feature to the GTF. start is 0-based.
		"""
		assert start < stop
		print(chromosome, 'Phasing', 'exon', start + 1, stop, '.', '+', '.',
			'gene_id "{}"; transcript_id "{}.1";'.format(name, name),
			sep='\t', file=self._file)

#chr1	Cufflinks	exon	11810	11844	.	+	.	gene_id "XLOC_000001"; transcript_id "CUFF.83.1";


def parse_pipe_notation(path):
	n = 0
	block_start = None
	singletons = 0
	block_lengths = []  # for statistics
	for record in vcf.Reader(filename=path):
		if not record.is_snp:
			continue
		if len(record.ALT) > 1:
			logger.warning("Reading VCFs with multiple ALTs not implemented")
			continue
		call = record.samples[0]
		assert len(record.samples) == 1
		if not call.is_het:
			continue

		if False:  # for debugging
			print(
				'{:10d}'.format(record.start),
				'alleles:', record.alleles,
				call.gt_alleles,
				'phased:', int(call.phased),
				'het:', int(call.is_het),
				'bases:', call.gt_bases
			)
		# Look for blocks of phased variants. According to the VCF specification,
		# the first variant in such blocks is marked as 'unphased'. Since it
		# needs to be considered part of the phased block, we keep track of the
		# position of the previous variant in prev_start.
		if call.phased:
			assert n > 0, "First variant in VCF is phased. This shouldn't be."
			# block_start is None when we're outside a block
			if block_start is None:
				# start a new block, but start it at the position of the
				# previous variant
				block_start = prev_start
				n_variants = 2  # this one and the one at prev_start
			else:
				n_variants += 1
		else:
			if block_start is not None:
				# end of block
				assert prev_start > block_start
				block_length = prev_start - block_start + 1
				print(record.CHROM, block_start, prev_start + 1, 'Len={},N={}'.format(block_length, n_variants), sep='\t')
				block_lengths.append(block_length)
				block_start = None
			else:
				singletons += 1

		prev_start = record.start
		n += 1
	if block_start is not None:
		assert prev_start > block_start
		block_length = prev_start - block_start + 1
		print(record.CHROM, block_start, prev_start + 1, 'Len={},N={}'.format(block_length, n_variants), sep='\t')
		block_lengths.append(block_length)

	# print statistics
	def printe(*args, **kwargs):
		kwargs['file'] = sys.stderr
		print(*args, **kwargs)

	printe('considered variants:', n)
	printe('blocks:', len(block_lengths))
	if blocks:
		printe('longest block:', max(block_lengths))
		printe('shortest block:', min(block_lengths))
		printe('average block: {:.2f}'.format(sum(block_lengths) / len(block_lengths)))
		printe('singletons (unphased variants not within a block):', singletons)


def parse_hp_tags(path, gtfpath=None):
	gtf = GtfWriter(gtfpath) if gtfpath else None
	n_phased = 0
	n_records = 0
	blocks = Counter()  # maps (chromosome, block_name) tuples to variant counts

	prev_phased = False
	prev_block_name = None
	prev_record = None

	for record in vcf.Reader(filename=path):
		n_records += 1
		assert len(record.samples) == 1
		call = record.samples[0]  # TODO allow to select a sample

		# GATK 3.1 does not support phasing sites with more than
		# two alleles, so there should not be phasing information.
		# See https://gatkforums.broadinstitute.org/discussion/4038 .
		assert not (len(record.ALT) > 1 and hasattr(call.data, 'HP'))
		assert not (not call.is_het and hasattr(call.data, 'HP')), "HP tag for homozygous variant found"

		if not hasattr(call.data, 'HP'):
			block_name = None
		else:
			assert len(call.data.HP) == 2
			# call.data.HP is something like: ['550267-1', '550267-2']
			block_name = call.data.HP[0].split('-')[0]
			blocks[(record.CHROM, block_name)] += 1
			n_phased += 1

		if prev_block_name != block_name or prev_record.CHROM != record.CHROM:
			# some type of transition is occurring here
			if prev_block_name is not None:
				# phased block has ended at previous variant
				if gtf:
					gtf.write(prev_record.CHROM, block_start, prev_record.start + 1, prev_block_name)
			if block_name is not None:
				# phased block starts
				block_start = record.start

		prev_block_name = block_name
		prev_record = record

	# print statistics
	def printe(*args, **kwargs):
		kwargs['file'] = sys.stderr
		print(*args, **kwargs)

	printe('Variants in VCF:', n_records)
	printe('Usable variants with phasing information:', n_phased)

	printe('blocks:', blocks)
	printe('No. of phased blocks:', len(blocks))
	if blocks:
		printe('Largest block:    ', max(blocks.values()))
		printe('Median block size:', sorted(blocks.values())[len(blocks) // 2])
		printe('Smallest block:   ', min(blocks.values()))


def main():
	logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

	parser = ArgumentParser(description=__doc__)
	#parser.add_argument('--pipeslash', action='store_true',
		#help='Parse the pipe/slash notation instead of HP tag.')
	parser.add_argument('--gtf', default=None,
		help='Write a GTF file visualizing the phased blocks.')
	parser.add_argument('vcf', help='VCF file')
	args = parser.parse_args()

	#if args.pipeslash:
		#parse_pipe_notation(args.vcf)
	#else:
	parse_hp_tags(args.vcf, gtfpath=args.gtf)


if __name__ == '__main__':
	main()