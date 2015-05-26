'''
Paths to files used or generated by the test harness
'''
from collections import Counter
from os import path as fp
import sys

from attelo.fold import (make_n_fold)
from attelo.harness import Harness
from attelo.harness.evaluate import (evaluate_corpus,
                                     prepare_dirs)
from attelo.io import (load_fold_dict,
                       save_fold_dict)
from attelo.util import (mk_rng)

from .local import (CONFIG_FILE,
                    DETAILED_EVALUATIONS,
                    EVALUATIONS,
                    FIXED_FOLD_FILE,
                    GRAPH_DOCS,
                    TEST_CORPUS,
                    TEST_EVALUATION_KEY,
                    TRAINING_CORPUS)
from .util import (latest_tmp, exit_ungathered)


# pylint: disable=too-many-arguments, too-many-instance-attributes
class IritHarness(Harness):
    """Test harness configuration using global vars defined in
    local.py
    """

    def __init__(self):
        dataset = fp.basename(TRAINING_CORPUS)
        testset = None if TEST_CORPUS is None\
            else fp.basename(TEST_CORPUS)
        super(IritHarness, self).__init__(dataset, testset)
        self.sanity_check_config()

    def run(self, runcfg):
        """Run the evaluation
        """
        data_dir = latest_tmp()
        if not fp.exists(data_dir):
            exit_ungathered()
        eval_dir, scratch_dir = prepare_dirs(runcfg, data_dir)
        self.load(runcfg, eval_dir, scratch_dir)
        evidence_of_gathered = self.mpack_paths(False)[0]
        if not fp.exists(evidence_of_gathered):
            exit_ungathered()
        evaluate_corpus(self)

    # ------------------------------------------------------
    # local settings
    # ------------------------------------------------------

    @property
    def config_files(self):
        return CONFIG_FILE

    @property
    def evaluations(self):
        return EVALUATIONS

    @property
    def detailed_evaluations(self):
        return DETAILED_EVALUATIONS

    @property
    def test_evaluation(self):
        if TEST_CORPUS is None:
            return None
        elif TEST_EVALUATION_KEY is None:
            return None
        test_confs = [x for x in self.evaluations
                      if x.key == TEST_EVALUATION_KEY]
        if test_confs:
            return test_confs[0]
        else:
            return None

    @property
    def graph_docs(self):
        return GRAPH_DOCS

    def create_folds(self, mpack):
        """
        Generate the folds file; return the resulting folds
        """
        if FIXED_FOLD_FILE is None:
            rng = mk_rng()
            fold_dict = make_n_fold(mpack, 10, rng)
        else:
            fold_dict = load_fold_dict(FIXED_FOLD_FILE)
        save_fold_dict(fold_dict, self.fold_file)
        return fold_dict

    # ------------------------------------------------------
    # paths
    # ------------------------------------------------------

    def _eval_data_path(self, ext, test_data=False):
        """
        Path to data file in the evaluation dir
        """
        dset = self.testset if test_data else self.dataset
        return fp.join(self.eval_dir, "%s.%s" % (dset, ext))

    def _model_basename(self, rconf, mtype, ext):
        "Basic filename for a model"

        if 'attach' in mtype:
            rsubconf = rconf.attach
        else:
            rsubconf = rconf.label

        template = '{dataset}.{learner}.{task}.{ext}'
        return template.format(dataset=self.dataset,
                               learner=rsubconf.key,
                               task=mtype,
                               ext=ext)

    def mpack_paths(self, test_data, stripped=False):
        ext = 'relations.sparse'
        core_path = self._eval_data_path(ext, test_data=test_data)
        return (core_path + '.edu_input',
                core_path + '.pairings',
                (core_path + '.stripped') if stripped else core_path,
                core_path + '.vocab')

    def model_paths(self, rconf, fold):
        if fold is None:
            parent_dir = self.combined_dir_path()
        else:
            parent_dir = self.fold_dir_path(fold)

        def _eval_model_path(mtype):
            "Model for a given loop/eval config and fold"
            bname = self._model_basename(rconf, mtype, 'model')
            return fp.join(parent_dir, bname)

        return {'attach': _eval_model_path("attach"),
                'label': _eval_model_path("relate"),
                'intra:attach': _eval_model_path("sent-attach"),
                'intra:label': _eval_model_path("sent-relate")}

    # ------------------------------------------------------
    # utility
    # ------------------------------------------------------

    def sanity_check_config(self):
        """
        Die if there's anything odd about the config
        """
        conf_counts = Counter(econf.key for econf in self.evaluations)
        bad_confs = [k for k, v in conf_counts.items() if v > 1]
        if bad_confs:
            oops = ("Sorry, there's an error in your configuration.\n"
                    "I don't dare to start evaluation until you fix it.\n"
                    "ERROR! -----------------vvvv---------------------\n"
                    "The following configurations more than once:{}\n"
                    "ERROR! -----------------^^^^^--------------------"
                    "").format("\n".join(bad_confs))
            sys.exit(oops)
        if TEST_EVALUATION_KEY is not None and self.test_evaluation is None:
            oops = ("Sorry, there's an error in your configuration.\n"
                    "I don't dare to start evaluation until you fix it.\n"
                    "ERROR! -----------------vvvv---------------------\n"
                    "The test configuration '{}' does not appear in your "
                    "configurations\n"
                    "ERROR! -----------------^^^^^--------------------"
                    "").format(TEST_EVALUATION_KEY)
            sys.exit(oops)
