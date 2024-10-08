#!/usr/bin/env python3

import argparse
import glob
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import zipfile

import pandas as pd
from isaagents import isatab
from isaagents.model import OntologyAnnotation
from isaagents.net import mtbls as MTBLS

logger = None

#    isaslicer.py <command> <study_id> [ command-specific options ]


def make_parser():
    parser = argparse.ArgumentParser( description="ISA slicer")

    parser.add_argument('--log-level', choices=[
        'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'],
        default='INFO', help="Set the desired logging level")

    subparsers = parser.add_subparsers(
        title='Actions',
        dest='command')  # specified subcommand will be available in attribute 'command'
    subparsers.required = True

    # mtblisa commands

    subparser = subparsers.add_parser(
        'mtbls-get-study-archive', aliases=['gsa'],
        help="Get ISA study from MetaboLights as zip archive")
    subparser.set_defaults(func=get_study_archive_command)
    subparser.add_argument('study_id')
    subparser.add_argument(
        'output', metavar="OUTPUT",
        help="Name of output archive (extension will be added)")
    subparser.add_argument('--format', metavar="FMT", choices=[
        'zip', 'tar', 'gztar', 'bztar', 'xztar'], default='zip',
        help="Type of archive to create")

    subparser = subparsers.add_parser('mtbls-get-study', aliases=['gs'],
                                      help="Get ISA study from MetaboLights")
    subparser.set_defaults(func=get_study_command)
    subparser.add_argument('study_id')
    subparser.add_argument('output', metavar="PATH", help="Name of output")
    subparser.add_argument(
        '-f', '--isa-format', choices=['isa-tab', 'isa-json'],
        metavar="FORMAT", default='isa-tab', help="Desired ISA format")

    subparser = subparsers.add_parser(
        'mtbls-get-factors', aliases=['gf'],
        help="Get factor names from a study in json format")
    subparser.set_defaults(func=get_factors_command)
    subparser.add_argument('study_id')
    subparser.add_argument(
        'output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output file")

    subparser = subparsers.add_parser(
        'mtbls-get-factor-values', aliases=['gfv'],
        help="Get factor values from a study in json format")
    subparser.set_defaults(func=get_factor_values_command)
    subparser.add_argument('study_id')
    subparser.add_argument(
        'factor', help="The desired factor. Use `get-factors` to get the list "
                       "of available factors")
    subparser.add_argument(
        'output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output file")

    subparser = subparsers.add_parser('mtbls-get-data-list', aliases=['gd'],
                                      help="Get data files list in json format")
    subparser.set_defaults(func=get_data_files_command)
    subparser.add_argument('study_id')
    subparser.add_argument('output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
                           help="Output file")
    subparser.add_argument(
        '--json-query',
        help="Factor query in JSON (e.g., '{\"Gender\":\"Male\"}'")
    subparser.add_argument(
        '--galaxy_parameters_file',
        help="Path to JSON file containing input Galaxy JSON")

    subparser = subparsers.add_parser(
        'mtbls-get-factors-summary', aliases=['gsum'],
        help="Get the variables summary from a study, in json format")
    subparser.set_defaults(func=get_summary_command)
    subparser.add_argument('study_id')
    subparser.add_argument(
        'json_output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output JSON file")
    subparser.add_argument(
        'html_output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output HTML file")

    # isaslicer commands on path to unpacked ISA-Tab as input

    subparser = subparsers.add_parser(
        'isa-tab-get-factors', aliases=['isagf'],
        help="Get factor names from a study in json format")
    subparser.set_defaults(func=isatab_get_factor_names_command)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab path")
    subparser.add_argument(
        'output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output file")

    subparser = subparsers.add_parser(
        'zip-get-factors', aliases=['zipgf'],
        help="Get factor names from a study in json format")
    subparser.set_defaults(func=zip_get_factor_names_command)
    subparser.add_argument('input_path', type=str,
                           help="Input ISA-Tab zip path")
    subparser.add_argument(
        'output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output file")

    subparser = subparsers.add_parser(
        'isa-tab-get-factor-values', aliases=['isagfv'],
        help="Get factor values from a study in json format")
    subparser.set_defaults(func=isatab_get_factor_values_command)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab path")
    subparser.add_argument(
        'factor', help="The desired factor. Use `get-factors` to get the list "
                       "of available factors")
    subparser.add_argument(
        'output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output file")

    subparser = subparsers.add_parser(
        'zip-get-factor-values', aliases=['zipgfv'],
        help="Get factor values from a study in json format")
    subparser.set_defaults(func=zip_get_factor_values_command)
    subparser.add_argument('input_path', type=str,
                           help="Input ISA-Tab zip path")
    subparser.add_argument(
        'factor', help="The desired factor. Use `get-factors` to get the list "
                       "of available factors")
    subparser.add_argument(
        'output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output file")

    subparser = subparsers.add_parser('isa-tab-get-data-list', aliases=['isagdl'],
                                      help="Get data files list in json format")
    subparser.set_defaults(func=isatab_get_data_files_list_command)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab path")
    subparser.add_argument('output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
                           help="Output file")
    subparser.add_argument(
        '--json-query',
        help="Factor query in JSON (e.g., '{\"Gender\":\"Male\"}'")
    subparser.add_argument(
        '--galaxy_parameters_file',
        help="Path to JSON file containing input Galaxy JSON")

    subparser = subparsers.add_parser('zip-get-data-list', aliases=['zipgdl'],
                                      help="Get data files list in json format")
    subparser.set_defaults(func=zip_get_data_files_list_command)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab zip path")
    subparser.add_argument('output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
                           help="Output file")
    subparser.add_argument(
        '--json-query',
        help="Factor query in JSON (e.g., '{\"Gender\":\"Male\"}'")
    subparser.add_argument(
        '--galaxy_parameters_file',
        help="Path to JSON file containing input Galaxy JSON")

    subparser = subparsers.add_parser('isa-tab-get-data-collection', aliases=['isagdc'],
                                      help="Get data files collection")
    subparser.set_defaults(func=isatab_get_data_files_collection_command)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab path")
    subparser.add_argument('output_path', type=str, help="Output data files path")
    subparser.add_argument(
        '--json-query',
        help="Factor query in JSON (e.g., '{\"Gender\":\"Male\"}'")
    subparser.add_argument(
        '--galaxy_parameters_file',
        help="Path to JSON file containing input Galaxy JSON")

    subparser = subparsers.add_parser('zip-get-data-collection', aliases=['zipgdc'],
                                      help="Get data files collection")
    subparser.set_defaults(func=zip_get_data_files_collection_command)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab zip path")
    subparser.add_argument('output_path', type=str, help="Output data files path")
    subparser.add_argument(
        '--json-query',
        help="Factor query in JSON (e.g., '{\"Gender\":\"Male\"}'")

    subparser = subparsers.add_parser(
        'isa-tab-get-factors-summary', aliases=['isasum'],
        help="Get the variables summary from a study, in json format")
    subparser.set_defaults(func=isatab_get_factors_summary_command)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab path")
    subparser.add_argument(
        'output', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
        help="Output file")

    subparser = subparsers.add_parser(
        'zip-get-factors-summary', aliases=['zipsum'],
        help="Get the variables summary from a study, in json format")
    subparser.set_defaults(func=zip_get_factors_summary_command)
    subparser.add_argument('input_path', type=str,
                           help="Input ISA-Tab zip path")
    subparser.add_argument(
        'json_output', nargs='?', type=argparse.FileType('w'),
        default=sys.stdout,
        help="Output JSON file")
    subparser.add_argument(
        'html_output', nargs='?', type=argparse.FileType('w'),
        default=sys.stdout,
        help="Output HTML file")

    subparser = subparsers.add_parser(
        'isaslicer2-slice', aliases=['slice2'],
        help="Slice ISA-Tabs version 2")
    subparser.set_defaults(func=query_isatab)
    subparser.add_argument('--source_dir', type=str,
                           help="Input ISA-Tab zip path")
    subparser.add_argument(
        '--galaxy_parameters_file', type=argparse.FileType(mode='r'),
        help="Path to JSON file containing input Galaxy JSON")
    subparser.add_argument('--output', type=argparse.FileType(mode='w'),
                           help="Input ISA-Tab zip path")

    subparser = subparsers.add_parser(
        'filter-data', aliases=['filter'],
        help="Filter out data based on slicer2")
    subparser.set_defaults(func=filter_data)
    subparser.add_argument('input_path', type=str, help="Input ISA-Tab path")
    subparser.add_argument('output_path', type=str, help="Output data files path")
    subparser.add_argument('--slice', type=argparse.FileType(mode='r'),
                           help="slice")
    subparser.add_argument('--filename_filter', type=str, help="shell-like wildcard to filter files")

    return parser


def filter_data(options):
    loglines = []
    source_dir = options.input_path if options.input_path else ""
    output_path = options.output_path
    filename_filter = options.filename_filter
    if source_dir:
        if not os.path.exists(source_dir):
            raise IOError('Source path does not exist!')
    data_files = []
    slice_json = options.slice
    for result in json.load(slice_json)['results']:
        data_files.extend(result.get('data_files', []))
    reduced_data_files = list(set(data_files))
    filtered_files = glob.glob(os.path.join(source_dir, filename_filter))
    to_copy = []
    for filepath in filtered_files:
        if os.path.basename(filepath) in reduced_data_files:
            to_copy.append(filepath)
    loglines.append("Using slice results from {}\n".format(slice_json.name))
    for filepath in to_copy:
        loglines.append("Copying {}\n".format(os.path.basename(filepath)))
        # try:
        #     shutil.copyfile(
        #         filepath, os.path.join(output_path, os.path.basename(filepath)))
        # except Exception as e:
        #     print(e)
        #     exit(1)
        try:
            os.symlink(
                filepath, os.path.join(output_path, os.path.basename(filepath)))
        except Exception as e:
            print(e)
            exit(1)
    with open('cli.log', 'w') as fp:
        fp.writelines(loglines)


def query_isatab(options):
    source_dir = options.source_dir if options.source_dir else ""
    galaxy_parameters_file = options.galaxy_parameters_file
    output = options.output

    debug = True
    if galaxy_parameters_file:
        galaxy_parameters = json.load(galaxy_parameters_file)
        print('Galaxy parameters:')
        print(json.dumps(galaxy_parameters, indent=4))
    else:
        raise IOError('Could not load Galaxy parameters file!')
    if source_dir:
        if not os.path.exists(source_dir):
            raise IOError('Source path does not exist!')
    query = galaxy_parameters['query']
    if debug:
        print('Query is:')
        print(json.dumps(query, indent=4))  # for debugging only
    if source_dir:
        investigation = isatab.load(source_dir)
    else:
        tmp = tempfile.mkdtemp()
        _ = MTBLS.get(galaxy_parameters['input']['mtbls_id'], tmp)
        investigation = isatab.load(tmp)
    # filter assays by mt/tt
    matching_assays = []
    mt = query.get('measurement_type').strip()
    tt = query.get('technology_type').strip()
    if mt and tt:
        for study in investigation.studies:
            matching_assays.extend(
                [x for x in study.assays if x.measurement_type.term == mt
                 and x.technology_type.term == tt])
    elif mt and not tt:
        for study in investigation.studies:
            matching_assays.extend(
                [x for x in study.assays if x.measurement_type.term == mt])
    elif not mt and tt:
        for study in investigation.studies:
            matching_assays.extend(
                [x for x in study.assays if x.technology_type.term == tt])
    else:
        for study in investigation.studies:
            matching_assays.extend(study.assays)
    assay_samples = []
    for assay in matching_assays:
        assay_samples.extend(assay.samples)
    if debug:
        print('Total samples: {}'.format(len(assay_samples)))

    # filter samples by fv
    factor_selection = {
        x.get('factor_name').strip(): x.get('factor_value').strip() for x in
        query.get('factor_selection', [])}

    fv_samples = set()
    if factor_selection:
        samples_to_remove = set()
        for f, v in factor_selection.items():
            for sample in assay_samples:
                for fv in [x for x in sample.factor_values if
                           x.factor_name.name == f]:
                    if isinstance(fv.value, OntologyAnnotation):
                        if fv.value.term == v:
                            fv_samples.add(sample)
                    elif fv.value == v:
                        fv_samples.add(sample)
        for f, v in factor_selection.items():
            for sample in fv_samples:
                for fv in [x for x in sample.factor_values if
                           x.factor_name.name == f]:
                    if isinstance(fv.value, OntologyAnnotation):
                        if fv.value.term != v:
                            samples_to_remove.add(sample)
                    elif fv.value != v:
                        samples_to_remove.add(sample)
        final_fv_samples = fv_samples.difference(samples_to_remove)
    else:
        final_fv_samples = assay_samples

    # filter samples by characteristic
    characteristics_selection = {
        x.get('characteristic_name').strip():
            x.get('characteristic_value').strip() for x in
            query.get('characteristics_selection', [])}

    cv_samples = set()
    if characteristics_selection:
        first_pass = True
        samples_to_remove = set()
        for c, v in characteristics_selection.items():
            if first_pass:
                for sample in final_fv_samples:
                    for cv in [x for x in sample.characteristics if
                               x.category.term == c]:
                        if isinstance(cv.value, OntologyAnnotation):
                            if cv.value.term == v:
                                cv_samples.add(sample)
                        elif cv.value == v:
                            cv_samples.add(sample)
                    for source in sample.derives_from:
                        for cv in [x for x in source.characteristics if
                                   x.category.term == c]:
                            if isinstance(cv.value, OntologyAnnotation):
                                if cv.value.term == v:
                                    cv_samples.add(sample)
                            elif cv.value == v:
                                cv_samples.add(sample)
                first_pass = False
            else:
                for sample in cv_samples:
                    for cv in [x for x in sample.characteristics if
                               x.category.term == c]:
                        if isinstance(cv.value, OntologyAnnotation):
                            if cv.value.term != v:
                                samples_to_remove.add(sample)
                        elif cv.value != v:
                            samples_to_remove.add(sample)
                    for source in sample.derives_from:
                        for cv in [x for x in source.characteristics if
                                   x.category.term == c]:
                            if isinstance(cv.value, OntologyAnnotation):
                                if cv.value.term != v:
                                    samples_to_remove.add(sample)
                            elif cv.value != v:
                                samples_to_remove.add(sample)
        final_cv_samples = cv_samples.difference(samples_to_remove)
    else:
        final_cv_samples = final_fv_samples

    # filter samples by process parameter
    parameters_selection = {
        x.get('parameter_name').strip():
            x.get('parameter_value').strip() for x in
        query.get('parameter_selection', [])}

    final_samples = final_cv_samples

    if debug:
        print('Final number of samples: {}'.format(len(final_samples)))
    results = []
    for sample in final_samples:
        results.append({
            'sample_name': sample.name,
            'data_files': []
        })
    for result in results:
        sample_name = result['sample_name']
        if source_dir:
            table_files = glob.iglob(os.path.join(source_dir, 'a_*'))
        else:
            table_files = glob.iglob(os.path.join(tmp, 'a_*'))
        for table_file in table_files:
            with open(table_file) as fp:
                df = isatab.load_table(fp)
                data_files = []
                table_headers = list(df.columns.values)
                sample_rows = df.loc[df['Sample Name'] == sample_name]
                data_node_labels = [
                    'Raw Data File', 'Raw Spectral Data File',
                    'Derived Spectral Data File',
                    'Derived Array Data File', 'Array Data File',
                    'Protein Assignment File', 'Peptide Assignment File',
                    'Post Translational Modification Assignment File',
                    'Acquisition Parameter Data File',
                    'Free Induction Decay Data File',
                    'Derived Array Data Matrix File', 'Image File',
                    'Derived Data File', 'Metabolite Assignment File']
                if parameters_selection:
                    for p, v in parameters_selection.items():
                        sample_pv_rows = sample_rows.loc[
                            sample_rows['Parameter Value[{}]'.format(p)] == v]
                        for node_label in data_node_labels:
                            if node_label in table_headers:
                                data_files.extend(
                                    list(sample_pv_rows[node_label]))
                    result['data_files'].extend(list(set(
                        i for i in list(data_files) if
                        str(i) not in ('nan', ''))))
                else:
                    for node_label in data_node_labels:
                        if node_label in table_headers:
                            data_files.extend(list(sample_rows[node_label]))
                    result['data_files'].extend(
                        list(set(i for i in list(data_files) if
                                 str(i) not in ('nan', ''))))
    results_json = {
        'query': query,
        'results': results
    }
    json.dump(results_json, output, indent=4)

    # if galaxy_parameters['input']['collection_output']:
    #     logger = logging.getLogger()
    #     logger.debug("copying data files to %s", os.path.dirname(output))
    #     for result in results:
    #         for data_file_name in result['data_files']:
    #             logging.info("Copying {}".format(data_file_name))
    #             shutil.copy(os.path.join(source_dir, data_file_name),
    #                         os.path.dirname(output))
    #     logger.info(
    #       "Finished writing data files to {}".format(os.path.dirname(output)))


def get_study_archive_command(options):
    study_id = options.study_id

    logger.info("Downloading study %s into archive at path %s.%s",
                study_id, options.output, options.format)

    tmpdir = MTBLS.get(study_id)
    logger.debug("MTBLS.get returned '%s'", tmpdir)
    if tmpdir is not None:
        try:
            shutil.make_archive(
                options.output, options.format, tmpdir, logger=logger)
            logger.info("ISA archive written")
        finally:
            logger.debug("Trying to clean up tmp dir %s", tmpdir)
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        raise RuntimeError("Error downloading ISA study")

# mtblisa commands


def get_study_command(options):
    if os.path.exists(options.output):
        raise RuntimeError("Selected output path {} already exists!".format(
            options.output))

    if options.isa_format == "isa-tab":
        tmp_data = None
        try:
            logger.info("Downloading study %s", options.study_id)
            tmp_data = MTBLS.get(options.study_id)
            if tmp_data is None:
                raise RuntimeError("Error downloading ISA study")

            logger.debug(
                "Finished downloading data. Moving to final location %s",
                options.output)
            shutil.move(tmp_data, options.output)
            logger.info("ISA archive written to %s", options.output)
        finally:
            if tmp_data:
                # try to clean up any temporary files left behind
                logger.debug("Deleting %s, if there's anything there", tmp_data)
                shutil.rmtree(tmp_data, ignore_errors=True)
    elif options.isa_format == "isa-json":
        isajson = MTBLS.getj(options.study_id)
        if isajson is None:
            raise RuntimeError("Error downloading ISA study")

        logger.debug(
            "Finished downloading data. Dumping json to final location %s",
            options.output)
        os.makedirs(options.output)
        json_file = os.path.join(options.output, "{}.json".format(
            isajson['identifier']))
        with open(json_file, 'w') as fd:
            json.dump(isajson, fd)
        logger.info("ISA-JSON written to %s", options.output)
    else:
        raise ValueError("BUG! Got an invalid isa format '{}'".format(
            options.isa_format))


def get_factors_command(options):
    logger.info("Getting factors for study %s. Writing to %s.",
                options.study_id, options.output.name)
    factor_names = MTBLS.get_factor_names(options.study_id)
    if factor_names is not None:
        json.dump(list(factor_names), options.output, indent=4)
        logger.debug("Factor names written")
    else:
        raise RuntimeError("Error downloading factors.")


def get_factor_values_command(options):
    logger.info("Getting values for factor {factor} in study {study_id}. Writing to {output_file}."
                .format(factor=options.factor, study_id=options.study_id, output_file=options.output.name))
    fvs = MTBLS.get_factor_values(options.study_id, options.factor)
    if fvs is not None:
        json.dump(list(fvs), options.output, indent=4)
        logger.debug("Factor values written to {}".format(options.output))
    else:
        raise RuntimeError("Error getting factor values")


def get_data_files_command(options):
    logger.info("Getting data files for study %s. Writing to %s.",
                options.study_id, options.output.name)
    if options.json_query:
        logger.debug("This is the specified query:\n%s", options.json_query)
        json_struct = json.loads(options.json_query)
        data_files = MTBLS.get_data_files(options.study_id, json_struct)
    elif options.galaxy_parameters_file:
        logger.debug("Using input Galaxy JSON parameters from:\n%s",
                     options.galaxy_parameters_file)
        with open(options.galaxy_parameters_file) as json_fp:
            galaxy_json = json.load(json_fp)
            json_struct = {}
            for fv_item in galaxy_json['factor_value_series']:
                json_struct[fv_item['factor_name']] = fv_item['factor_value']
            data_files = MTBLS.get_data_files(options.study_id, json_struct)
    else:
        logger.debug("No query was specified")
        data_files = MTBLS.get_data_files(options.study_id)

    logger.debug("Result data files list: %s", data_files)
    if data_files is None:
        raise RuntimeError("Error getting data files with isaagents")

    logger.debug("dumping data files to %s", options.output.name)
    json.dump(list(data_files), options.output, indent=4)
    logger.info("Finished writing data files to {}".format(options.output))


def build_html_data_files_list(data_files_list):
    data_files_table = '<table>'
    data_files_table += '<tr><th>Sample Name</th><th>Data File Names</th></tr>'
    for data_file in data_files_list:
        sample_name = data_file['sample']
        data_files = ', '.join(data_file['data_files'])
        data_files_table += '<tr><td>{sample_name}</td><td>{data_files}</td>' \
            .format(sample_name=sample_name, data_files=data_files)
    html_data_files_list = """
    <html>
    <head>
    <title>ISA-Tab Factors Summary</title>
    </head>
    <body>
    {summary_table}
    </body>
    </html>
""".format(summary_table=data_files_table)
    return html_data_files_list


def build_html_summary(summary):
    study_groups = {}
    for item in summary:
        sample_name = item['sample_name']
        study_factors = []
        for item in [x for x in item.items() if x[0] != "sample_name"]:
            study_factors.append(': '.join([item[0], item[1]]))
        study_group = ', '.join(study_factors)
        if study_group not in study_groups.keys():
            study_groups[study_group] = []
        study_groups[study_group].append(sample_name)
    summary_table = '<table>'
    summary_table += '<tr><th>Study group</th><th>Number of samples</th></tr>'
    for item in study_groups.items():
        study_group = item[0]
        num_samples = len(item[1])
        summary_table += '<tr><td>{study_group}</td><td>{num_samples}</td>' \
            .format(study_group=study_group, num_samples=num_samples)
    summary_table += '</table>'
    html_summary = """
<html>
<head>
<title>ISA-Tab Factors Summary</title>
</head>
<body>
{summary_table}
</body>
</html>
""".format(summary_table=summary_table)
    return html_summary


def get_summary_command(options):
    logger.info("Getting summary for study %s. Writing to %s.",
                options.study_id, options.json_output.name)

    summary = MTBLS.get_study_variable_summary(options.study_id)
    # new_summary = []
    # for item in summary:
    #     new_summary.append(
    #         {k: v for k, v in item.items() if k is not "sample_name"})
    # summary = new_summary
    if summary is not None:
        json.dump(summary, options.json_output, indent=4)
        logger.debug("Summary dumped to JSON")
        html_summary = build_html_summary(summary)
        with options.html_output as html_fp:
            html_fp.write(html_summary)
    else:
        raise RuntimeError("Error getting study summary")


# isaslicer commands

def isatab_get_data_files_list_command(options):
    logger.info("Getting data files for study %s. Writing to %s.",
                options.input_path, options.output.name)
    if options.json_query:
        logger.debug("This is the specified query:\n%s", options.json_query)
        json_struct = json.loads(options.json_query)
    elif options.galaxy_parameters_file:
        logger.debug("Using input Galaxy JSON parameters from:\n%s",
                     options.galaxy_parameters_file)
        with open(options.galaxy_parameters_file) as json_fp:
            galaxy_json = json.load(json_fp)
            json_struct = {}
            for fv_item in galaxy_json['factor_value_series']:
                json_struct[fv_item['factor_name']] = fv_item['factor_value']
    else:
        logger.debug("No query was specified")
        json_struct = None
    factor_selection = json_struct
    input_path = options.input_path
    result = slice_data_files(input_path, factor_selection=factor_selection)
    data_files = result
    logger.debug("Result data files list: %s", data_files)
    if data_files is None:
        raise RuntimeError("Error getting data files with isaagents")

    logger.debug("dumping data files to %s", options.output.name)
    json.dump(list(data_files), options.output, indent=4)
    logger.info("Finished writing data files to {}".format(options.output))


def zip_get_data_files_list_command(options):
    logger.info("Getting data files for study %s. Writing to %s.",
                options.input_path, options.output.name)
    if options.json_query:
        logger.debug("This is the specified query:\n%s", options.json_query)
        json_struct = json.loads(options.json_query)
    elif options.galaxy_parameters_file:
        logger.debug("Using input Galaxy JSON parameters from:\n%s",
                     options.galaxy_parameters_file)
        with open(options.galaxy_parameters_file) as json_fp:
            galaxy_json = json.load(json_fp)
            json_struct = {}
            for fv_item in galaxy_json['factor_value_series']:
                json_struct[fv_item['factor_name']] = fv_item['factor_value']
    else:
        logger.debug("No query was specified")
        json_struct = None
    factor_selection = json_struct
    input_path = options.input_path
    with zipfile.ZipFile(input_path) as zfp:
        tmpdir = tempfile.mkdtemp()
        zfp.extractall(path=tmpdir)
        result = slice_data_files(tmpdir, factor_selection=factor_selection)
        data_files = result
        logger.debug("Result data files list: %s", data_files)
    if data_files is None:
        raise RuntimeError("Error getting data files with isaagents")
    logger.debug("dumping data files to %s", options.output.name)
    json.dump(list(data_files), options.output, indent=4)
    logger.info("Finished writing data files to {}".format(options.output))
    shutil.rmtree(tmpdir)


def isatab_get_data_files_collection_command(options):
    logger.info("Getting data files for study %s. Writing to %s.",
                options.input_path, options.output_path)
    if options.json_query:
        logger.debug("This is the specified query:\n%s", options.json_query)
    else:
        logger.debug("No query was specified")
    input_path = options.input_path
    if options.json_query is not None:
        json_struct = json.loads(options.json_query)
    elif options.galaxy_parameters_file:
        logger.debug("Using input Galaxy JSON parameters from:\n%s",
                     options.galaxy_parameters_file)
        with open(options.galaxy_parameters_file) as json_fp:
            galaxy_json = json.load(json_fp)
            json_struct = {}
            for fv_item in galaxy_json['factor_value_series']:
                json_struct[fv_item['factor_name']] = fv_item['factor_value']
    else:
        logger.debug("No query was specified")
        json_struct = None
    factor_selection = json_struct
    result = slice_data_files(input_path, factor_selection=factor_selection)
    data_files = result
    logger.debug("Result data files list: %s", data_files)
    if data_files is None:
        raise RuntimeError("Error getting data files with isaagents")
    output_path = options.output_path
    logger.debug("copying data files to %s", output_path)
    for result in data_files:
        for data_file_name in result['data_files']:
            logging.info("Copying {}".format(data_file_name))
            shutil.copy(os.path.join(input_path, data_file_name), output_path)
    logger.info("Finished writing data files to {}".format(output_path))


def zip_get_data_files_collection_command(options):
    logger.info("Getting data files for study %s. Writing to %s.",
                options.input_path, options.output_path)
    if options.json_query:
        logger.debug("This is the specified query:\n%s", options.json_query)
    else:
        logger.debug("No query was specified")
    input_path = options.input_path
    output_path = options.output_path
    if options.json_query is not None:
        json_struct = json.loads(options.json_query)
        factor_selection = json_struct
    else:
        factor_selection = None
    with zipfile.ZipFile(input_path) as zfp:
        tmpdir = tempfile.mkdtemp()
        zfp.extractall(path=tmpdir)
        result = slice_data_files(tmpdir, factor_selection=factor_selection)
        data_files = result
        logger.debug("Result data files list: %s", data_files)
        if data_files is None:
            raise RuntimeError("Error getting data files with isaagents")
        logger.debug("copying data files to %s", output_path)
        for result in data_files:
            for data_file_name in result['data_files']:
                logging.info("Copying {}".format(data_file_name))
                shutil.copy(os.path.join(tmpdir, data_file_name), output_path)
    logger.info("Finished writing data files to {}".format(output_path))
    shutil.rmtree(tmpdir)


def slice_data_files(dir, factor_selection=None):
    results = []
    # first collect matching samples
    for table_file in glob.iglob(os.path.join(dir, '[a|s]_*')):
        logger.info('Loading {table_file}'.format(table_file=table_file))

        with open(os.path.join(dir, table_file)) as fp:
            df = isatab.load_table(fp)

            if factor_selection is None:
                matches = df['Sample Name'].items()

                for indx, match in matches:
                    sample_name = match
                    if len([r for r in results if r['sample'] ==
                            sample_name]) == 1:
                        continue
                    else:
                        results.append(
                            {
                                'sample': sample_name,
                                'data_files': []
                            }
                        )

            else:
                for factor_name, factor_value in factor_selection.items():
                    if 'Factor Value[{}]'.format(factor_name) in list(
                            df.columns.values):
                        matches = df.loc[df['Factor Value[{factor}]'.format(
                            factor=factor_name)] == factor_value][
                            'Sample Name'].items()

                        for indx, match in matches:
                            sample_name = match
                            if len([r for r in results if r['sample'] ==
                                    sample_name]) == 1:
                                continue
                            else:
                                results.append(
                                    {
                                        'sample': sample_name,
                                        'data_files': [],
                                        'query_used': factor_selection
                                    }
                                )

    # now collect the data files relating to the samples
    for result in results:
        sample_name = result['sample']

        for table_file in glob.iglob(os.path.join(dir, 'a_*')):
            with open(table_file) as fp:
                df = isatab.load_table(fp)

                data_files = []

                table_headers = list(df.columns.values)
                sample_rows = df.loc[df['Sample Name'] == sample_name]

                data_node_labels = [
                    'Raw Data File',
                    'Raw Spectral Data File',
                    'Derived Spectral Data File',
                    'Derived Array Data File',
                    'Array Data File',
                    'Protein Assignment File',
                    'Peptide Assignment File',
                    'Post Translational Modification Assignment File',
                    'Acquisition Parameter Data File',
                    'Free Induction Decay Data File',
                    'Derived Array Data Matrix File',
                    'Image File',
                    'Derived Data File',
                    'Metabolite Assignment File']
                for node_label in data_node_labels:
                    if node_label in table_headers:
                        data_files.extend(list(sample_rows[node_label]))

                result['data_files'] = [i for i in list(data_files) if
                                        str(i) != 'nan']
    return results


def isatab_get_factor_names_command(options):
    input_path = options.input_path
    logger.info("Getting factors for study %s. Writing to %s.",
                input_path, options.output.name)
    _RX_FACTOR_VALUE = re.compile(r'Factor Value\[(.*?)\]')
    factors = set()
    for table_file in glob.iglob(os.path.join(input_path, '[a|s]_*')):
        with open(os.path.join(input_path, table_file)) as fp:
            df = isatab.load_table(fp)

            factors_headers = [header for header in list(df.columns.values)
                               if _RX_FACTOR_VALUE.match(header)]

            for header in factors_headers:
                factors.add(header[13:-1])
    if factors is not None:
        json.dump(list(factors), options.output, indent=4)
        logger.debug("Factor names written")
    else:
        raise RuntimeError("Error reading factors.")


def zip_get_factor_names_command(options):
    input_path = options.input_path
    logger.info("Getting factors for study %s. Writing to %s.",
                input_path, options.output.name)
    # unpack input_path
    with zipfile.ZipFile(input_path) as zfp:
        tmpdir = tempfile.mkdtemp()
        zfp.extractall(path=tmpdir)
        _RX_FACTOR_VALUE = re.compile(r'Factor Value\[(.*?)\]')
        factors = set()
        for table_file in glob.iglob(os.path.join(tmpdir, '[a|s]_*')):
            logging.info('Searching {}'.format(table_file))
            with open(os.path.join(tmpdir, table_file)) as fp:
                df = isatab.load_table(fp)

                factors_headers = [header for header in list(df.columns.values)
                                   if _RX_FACTOR_VALUE.match(header)]

                for header in factors_headers:
                    factors.add(header[13:-1])
    if factors is not None:
        json.dump(list(factors), options.output, indent=4)
        logger.debug("Factor names written")
    else:
        raise RuntimeError("Error reading factors.")
    shutil.rmtree(tmpdir)


def isatab_get_factor_values_command(options):
    logger.info("Getting values for factor {factor} in study {input_path}. Writing to {output_file}."
                .format(factor=options.factor, input_path=options.input_path, output_file=options.output.name))
    fvs = set()

    input_path = options.input_path
    factor_name = options.factor

    for table_file in glob.iglob(os.path.join(input_path, '[a|s]_*')):
        with open(os.path.join(input_path, table_file)) as fp:
            df = isatab.load_table(fp)

            if 'Factor Value[{factor}]'.format(factor=factor_name) in \
                    list(df.columns.values):
                for _, match in df[
                    'Factor Value[{factor}]'.format(
                        factor=factor_name)].iteritems():
                    try:
                        match = match.item()
                    except AttributeError:
                        pass

                    if isinstance(match, (str, int, float)):
                        if str(match) != 'nan':
                            fvs.add(match)
    if fvs is not None:
        json.dump(list(fvs), options.output, indent=4)
        logger.debug("Factor values written to {}".format(options.output))
    else:
        raise RuntimeError("Error getting factor values")


def zip_get_factor_values_command(options):
    input_path = options.input_path
    logger.info("Getting factors for study %s. Writing to %s.",
                input_path, options.output.name)
    logger.info("Getting values for factor {factor} in study {input_path}. "
                "Writing to {output_file}.".format(
                    factor=options.factor, input_path=options.input_path,
                    output_file=options.output.name))
    fvs = set()
    factor_name = options.factor

    # unpack input_path
    with zipfile.ZipFile(input_path) as zfp:
        tmpdir = tempfile.mkdtemp()
        zfp.extractall(path=tmpdir)
        for table_file in glob.glob(os.path.join(tmpdir, '[a|s]_*')):
            logging.info('Searching {}'.format(table_file))
            with open(os.path.join(input_path, table_file)) as fp:
                df = isatab.load_table(fp)
                if 'Factor Value[{factor}]'.format(factor=factor_name) in \
                        list(df.columns.values):
                    for _, match in df[
                        'Factor Value[{factor}]'.format(
                            factor=factor_name)].iteritems():
                        try:
                            match = match.item()
                        except AttributeError:
                            pass

                        if isinstance(match, (str, int, float)):
                            if str(match) != 'nan':
                                fvs.add(match)
    if fvs is not None:
        json.dump(list(fvs), options.output, indent=4)
        logger.debug("Factor values written to {}".format(options.output))
    else:
        raise RuntimeError("Error getting factor values")
    shutil.rmtree(tmpdir)


def isatab_get_factors_summary_command(options):
    logger.info("Getting summary for study %s. Writing to %s.",
                options.input_path, options.output.name)
    input_path = options.input_path
    ISA = isatab.load(input_path)

    all_samples = []
    for study in ISA.studies:
        all_samples.extend(study.samples)

    samples_and_fvs = []

    for sample in all_samples:
        sample_and_fvs = {
            'sample_name': sample.name,
        }

        for fv in sample.factor_values:
            if isinstance(fv.value, (str, int, float)):
                fv_value = fv.value
                sample_and_fvs[fv.factor_name.name] = fv_value
            elif isinstance(fv.value, OntologyAnnotation):
                fv_value = fv.value.term
                sample_and_fvs[fv.factor_name.name] = fv_value

        samples_and_fvs.append(sample_and_fvs)

    df = pd.DataFrame(samples_and_fvs)
    nunique = df.apply(pd.Series.nunique)
    cols_to_drop = nunique[nunique == 1].index

    df = df.drop(cols_to_drop, axis=1)
    summary = df.to_dict(orient='records')
    if summary is not None:
        json.dump(summary, options.output, indent=4)
        logger.debug("Summary dumped to JSON")
        # html_summary = build_html_summary(summary)
        # with options.html_output as html_fp:
        #     html_fp.write(html_summary)
    else:
        raise RuntimeError("Error getting study summary")


def zip_get_factors_summary_command(options):
    logger.info("Getting summary for study %s. Writing to %s.",
                options.input_path, options.json_output.name)
    input_path = options.input_path
    with zipfile.ZipFile(input_path) as zfp:
        tmpdir = tempfile.mkdtemp()
        zfp.extractall(path=tmpdir)
        ISA = isatab.load(tmpdir)
        all_samples = []
        for study in ISA.studies:
            all_samples.extend(study.samples)
        samples_and_fvs = []
        for sample in all_samples:
            sample_and_fvs = {
                'sample_name': sample.name,
            }
            for fv in sample.factor_values:
                if isinstance(fv.value, (str, int, float)):
                    fv_value = fv.value
                    sample_and_fvs[fv.factor_name.name] = fv_value
                elif isinstance(fv.value, OntologyAnnotation):
                    fv_value = fv.value.term
                    sample_and_fvs[fv.factor_name.name] = fv_value
            samples_and_fvs.append(sample_and_fvs)
        df = pd.DataFrame(samples_and_fvs)
        nunique = df.apply(pd.Series.nunique)
        cols_to_drop = nunique[nunique == 1].index
        df = df.drop(cols_to_drop, axis=1)
        summary = df.to_dict(orient='records')
    if summary is not None:
        json.dump(summary, options.json_output, indent=4)
        logger.debug("Summary dumped to JSON")
        print(json.dumps(summary, indent=4))
        html_summary = build_html_summary(summary)
        with options.html_output as html_fp:
            html_fp.write(html_summary)
    else:
        raise RuntimeError("Error getting study summary")
    shutil.rmtree(tmpdir)


def get_study_groups(input_path):
    factors_summary = isatab_get_factors_summary_command(input_path=input_path)
    study_groups = {}

    for factors_item in factors_summary:
        fvs = tuple(factors_item[k] for k in factors_item.keys() if k != 'name')

        if fvs in study_groups.keys():
            study_groups[fvs].append(factors_item['name'])
        else:
            study_groups[fvs] = [factors_item['name']]
    return study_groups


def get_study_groups_samples_sizes(input_path):
    study_groups = get_study_groups(input_path=input_path)
    return list(map(lambda x: (x[0], len(x[1])), study_groups.items()))


def get_sources_for_sample(input_path, sample_name):
    ISA = isatab.load(input_path)
    hits = []

    for study in ISA.studies:
        for sample in study.samples:
            if sample.name == sample_name:
                print('found a hit: {sample_name}'.format(
                    sample_name=sample.name))

                for source in sample.derives_from:
                    hits.append(source.name)
    return hits


def get_data_for_sample(input_path, sample_name):
    ISA = isatab.load(input_path)
    hits = []
    for study in ISA.studies:
        for assay in study.assays:
            for data in assay.data_files:
                if sample_name in [x.name for x in data.generated_from]:
                    logger.info('found a hit: {filename}'.format(
                        filename=data.filename))
                    hits.append(data)
    return hits


def get_study_groups_data_sizes(input_path):
    study_groups = get_study_groups(input_path=input_path)
    return list(map(lambda x: (x[0], len(x[1])), study_groups.items()))


def get_characteristics_summary(input_path):
    """
        This function generates a characteristics summary for a MetaboLights
        study

        :param input_path: Input path to ISA-tab
        :return: A list of dicts summarising the set of characteristic names
        and values associated with each sample

        Note: it only returns a summary of characteristics with variable values.

        Example usage:
            characteristics_summary = get_characteristics_summary('/path/to/my/study/')
            [
                {
                    "name": "6089if_9",
                    "Variant": "Synechocystis sp. PCC 6803.sll0171.ko"
                },
                {
                    "name": "6089if_43",
                    "Variant": "Synechocystis sp. PCC 6803.WT.none"
                },
            ]


        """
    ISA = isatab.load(input_path)

    all_samples = []
    for study in ISA.studies:
        all_samples.extend(study.samples)

    samples_and_characs = []
    for sample in all_samples:
        sample_and_characs = {
            'name': sample.name
        }

        for source in sample.derives_from:
            for c in source.characteristics:
                if isinstance(c.value, (str, int, float)):
                    c_value = c.value
                    sample_and_characs[c.category.term] = c_value
                elif isinstance(c.value, OntologyAnnotation):
                    c_value = c.value.term
                    sample_and_characs[c.category.term] = c_value

        samples_and_characs.append(sample_and_characs)

    df = pd.DataFrame(samples_and_characs)
    nunique = df.apply(pd.Series.nunique)
    cols_to_drop = nunique[nunique == 1].index

    df = df.drop(cols_to_drop, axis=1)
    return df.to_dict(orient='records')


def get_study_variable_summary(input_path):
    ISA = isatab.load(input_path)

    all_samples = []
    for study in ISA.studies:
        all_samples.extend(study.samples)

    samples_and_variables = []
    for sample in all_samples:
        sample_and_vars = {
            'sample_name': sample.name
        }

        for fv in sample.factor_values:
            if isinstance(fv.value, (str, int, float)):
                fv_value = fv.value
                sample_and_vars[fv.factor_name.name] = fv_value
            elif isinstance(fv.value, OntologyAnnotation):
                fv_value = fv.value.term
                sample_and_vars[fv.factor_name.name] = fv_value

        for source in sample.derives_from:
            sample_and_vars['source_name'] = source.name
            for c in source.characteristics:
                if isinstance(c.value, (str, int, float)):
                    c_value = c.value
                    sample_and_vars[c.category.term] = c_value
                elif isinstance(c.value, OntologyAnnotation):
                    c_value = c.value.term
                    sample_and_vars[c.category.term] = c_value

        samples_and_variables.append(sample_and_vars)

    df = pd.DataFrame(samples_and_variables)
    nunique = df.apply(pd.Series.nunique)
    cols_to_drop = nunique[nunique == 1].index

    df = df.drop(cols_to_drop, axis=1)
    return df.to_dict(orient='records')


def get_study_group_factors(input_path):
    factors_list = []

    for table_file in glob.iglob(os.path.join(input_path, '[a|s]_*')):
        with open(os.path.join(input_path, table_file)) as fp:
            df = isatab.load_table(fp)

            factor_columns = [x for x in df.columns if x.startswith(
                'Factor Value')]
            if len(factor_columns) > 0:
                factors_list = df[factor_columns].drop_duplicates()\
                    .to_dict(orient='records')
    return factors_list


def get_filtered_df_on_factors_list(input_path):
    factors_list = get_study_group_factors(input_path=input_path)
    queries = []

    for item in factors_list:
        query_str = []

        for k, v in item.items():
            k = k.replace(' ', '_').replace('[', '_').replace(']', '_')
            if isinstance(v, str):
                v = v.replace(' ', '_').replace('[', '_').replace(']', '_')
                query_str.append("{k} == '{v}' and ".format(k=k, v=v))

        query_str = ''.join(query_str)[:-4]
        queries.append(query_str)

    for table_file in glob.iglob(os.path.join(input_path, '[a|s]_*')):
        with open(os.path.join(input_path, table_file)) as fp:
            df = isatab.load_table(fp)

            cols = df.columns
            cols = cols.map(
                lambda x: x.replace(' ', '_') if isinstance(x, str) else x)
            df.columns = cols

            cols = df.columns
            cols = cols.map(
                lambda x: x.replace('[', '_') if isinstance(x, str) else x)
            df.columns = cols

            cols = df.columns
            cols = cols.map(
                lambda x: x.replace(']', '_') if isinstance(x, str) else x)
            df.columns = cols

        for query in queries:
            # query uses pandas.eval, which evaluates queries like pure Python
            # notation
            df2 = df.query(query)
            if 'Sample_Name' in df.columns:
                print('Group: {query} / Sample_Name: {sample_name}'.format(
                    query=query, sample_name=list(df2['Sample_Name'])))

            if 'Source_Name' in df.columns:
                print('Group: {} / Sources_Name: {}'.format(
                    query, list(df2['Source_Name'])))

            if 'Raw_Spectral_Data_File' in df.columns:
                print('Group: {query} / Raw_Spectral_Data_File: {filename}'
                      .format(query=query[13:-2],
                              filename=list(df2['Raw_Spectral_Data_File'])))
    return queries


def datatype_get_summary_command(options):
    logger.info("Getting summary for study %s. Writing to %s.",
                options.study_id, options.output.name)

    summary = get_study_variable_summary(options.study_id)
    print('summary: ', list(summary))
    if summary is not None:
        json.dump(summary, options.output, indent=4)
        logger.debug("Summary dumped")
    else:
        raise RuntimeError("Error getting study summary")


# logging and argument parsing

def _configure_logger(options):
    logging_level = getattr(logging, options.log_level, logging.INFO)
    logging.basicConfig(level=logging_level)

    global logger
    logger = logging.getLogger()
    logger.setLevel(logging_level)  # there's a bug somewhere.  The level set through basicConfig isn't taking effect


def _parse_args(args):
    parser = make_parser()
    options = parser.parse_args(args)
    return options


def main(args):
    options = _parse_args(args)
    _configure_logger(options)
    # run subcommand
    options.func(options)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
        sys.exit(0)
    except Exception as e:
        logger.exception(e)
        logger.error(e)
        sys.exit(e.code if hasattr(e, "code") else 99)
