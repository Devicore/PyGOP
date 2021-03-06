#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Homogeneous Multilayer Generalized Operational Perceptron
https://arxiv.org/abs/1804.05093


Author: Dat Tran
Email: dat.tranthanh@tut.fi, viebboy@gmail.com
github: https://github.com/viebboy
"""
from __future__ import print_function


from ..utility import misc, gop_utils, gop_operators
from ._model import _Model
import shutil
import os
import copy
import pickle


class HoMLGOP(_Model):
    """Homogeneous Multilayer Generalized Operational Perceptron (HoMLGOP) model

    This class implements the HoMLGOP algorithm to learn a homogeneous multilayer
    network of Generalized Operational Perceptron (GOP) in a progressive manner by
    incrementing the neuron blocks in a layer and incrementing the layers.
    Different than HeMLGOP, this algorithm enforces all GOPs within a layer having
    the same operator set, hence the term homogenous.

    Note:
        The model basically uses a python data generator mechanism to feed the data
        Thus, the data should be prepared with the following format:
            train_func: a function that returns (data_generator, number of steps)
                        the user specifies how data is loaded and preprocess by giving
                        the definition of the data generator and the number of steps (number of mini-batches)
            train_data: the input to 'train_func'
                        this can be filepath to the data on disk

        When the model generates the data, the generator and #steps are retrieved by
        calling:
            gen, steps = train_func(train_data)

        And next(gen) should produce a mini-batch of (x,y) in case of fit()/evaluate()
        or only x in case of predict()

        See documentation page for example how to define such train_func and train_data


    Examples:
        >>> from GOP import models
        >>> model = models.HoMLGOP() # create a model instance
        >>> params = model.get_default_parameters() # get default parameters

        # fit the model with data using train_func, train_data (see above in Note)
        >>> performance, progressive_history, finetune_history = model.fit(params, train_func, train_data)

        # evaluate model with test data (test_func, test_data) using a list of metrics
        # and special_metrics (those require full batch evaluation such as F1, Precision, Recall...)
        # using either CPU or GPU as computation environment,
        # e.g. computation=('cpu',) -> using cpu
        # e.g. computation=('gpu', [0,1]) -> using gpu with GPU0, GPU1

        >>> model.evaluate(test_func, test_data, metrics, special_metrics, computation)

        # generate prediction with (test_func, test_data)
        >>> model.predict(test_func, test_data, computation)

        # save model to 'homlgop.pickle'
        >>> model.save('homlgop.pickle')

        # load model from 'homlgop.pickle' and finetune with another data and
        # (possibly different) parameter settings
        >>> model.load('homlgop.pickle')
        >>> history, performance = model.finetune(params, another_train_func, another_train_data)

        See documentation page for detail usage and explanation


    """

    def __init__(self,):
        self.model_data = None
        self.model_data_attributes = ['model',
                                      'topology',
                                      'op_sets',
                                      'weights',
                                      'output_activation',
                                      'use_bias']

        self.model_name = 'HoMLGOP'

        return

    def get_default_parameters(self,):

        params = {'least_square_regularizer': 0.1,
                  'block_threshold': 1e-4,
                  'layer_threshold': 1e-4,
                  'metrics': ['mse', ],
                  'convergence_measure': 'mse',
                  'direction': 'lower',
                  'output_activation': None,
                  'loss': 'mse',
                  'max_block': 5,
                  'block_size': 20,
                  'max_layer': 4,
                  'weight_regularizer': None,
                  'weight_regularizer_finetune': None,
                  'weight_constraint': 2.0,
                  'weight_constraint_finetune': 2.0,
                  'lr_train': (1e-3, 1e-4, 1e-5),
                  'epoch_train': (2, 2, 2),
                  'lr_finetune': (1e-3, 1e-4, 1e-5),
                  'epoch_finetune': (2, 2, 2),
                  'input_dropout': None,
                  'dropout': 0.2,
                  'dropout_finetune': 0.2,
                  'optimizer': 'adam',
                  'optimizer_parameters': None,
                  'nodal_set': gop_operators.get_default_nodal_set(),
                  'pool_set': gop_operators.get_default_pool_set(),
                  'activation_set': gop_operators.get_default_activation_set(),
                  'direct_computation': False,
                  'cluster': False,
                  'special_metrics': None,
                  'search_computation': ('cpu', 8),
                  'finetune_computation': ('cpu', 8),
                  'use_bias': True,
                  'class_weight': None}

        return params

    def fit(self,
            params,
            train_func,
            train_data,
            val_func=None,
            val_data=None,
            test_func=None,
            test_data=None,
            verbose=False):

        if verbose:
            print('Start progressive learning')

        p_history = self.progressive_learn(params,
                                           train_func,
                                           train_data,
                                           val_func,
                                           val_data,
                                           test_func,
                                           test_data,
                                           verbose)

        if verbose:
            print('Start finetuning')

        f_history, performance = self.finetune(params,
                                               train_func,
                                               train_data,
                                               val_func,
                                               val_data,
                                               test_func,
                                               test_data,
                                               verbose)

        if os.path.exists(os.path.join(params['tmp_dir'], params['model_name'])):
            shutil.rmtree(os.path.join(params['tmp_dir'], params['model_name']))

        return performance, p_history, f_history

    def progressive_learn(self,
                          params,
                          train_func,
                          train_data,
                          val_func=None,
                          val_data=None,
                          test_func=None,
                          test_data=None,
                          verbose=False):

        params = self.check_parameters(params)

        original_convergence_measure = params['convergence_measure']
        if val_func:
            params['convergence_measure'] = 'val_' + params['convergence_measure']
        else:
            params['convergence_measure'] = 'train_' + params['convergence_measure']

        misc.test_generator(train_func, train_data, params['input_dim'], params['output_dim'])
        if val_func:
            misc.test_generator(val_func, val_data, params['input_dim'], params['output_dim'])
        if test_func:
            misc.test_generator(test_func, test_data, params['input_dim'], params['output_dim'])

        train_states = misc.initialize_states(params, self.model_name)

        if not train_states['is_finished']:
            for layer_iter in range(train_states['layer_iter'], params['max_layer']):
                block_stop = False
                for block_iter in range(train_states['block_iter'], params['max_block']):

                    if block_iter == 0:
                        if layer_iter > 0:
                            train_states['topology'].pop()

                        train_states['topology'].append([])
                        train_states['topology'].append(('dense', params['output_dim']))
                        train_states['history'].append([])
                        train_states['measure'].append([])

                    if verbose:
                        print('-------------Layer %d ---------------Block %d ------------------' %
                              (layer_iter, block_iter))

                    if block_iter == 0:
                        if verbose:
                            print('##### Iterative Randomized Search #####')

                        if params['cluster']:
                            search_routine = gop_utils.search_cluster
                        else:
                            if params['search_computation'][0] == 'cpu':
                                search_routine = gop_utils.search_cpu
                            else:
                                search_routine = gop_utils.search_gpu

                        # operator set evaluation
                        _, block_weights, block_op_set_idx, _ = search_routine(params,
                                                                               train_states,
                                                                               train_func,
                                                                               train_data,
                                                                               val_func,
                                                                               val_data,
                                                                               test_func,
                                                                               test_data)

                    else:

                        suffix = '_' + str(layer_iter) + '_' + str(block_iter - 1)
                        block_op_set_idx = train_states['op_set_indices']['gop' + suffix]
                        block_weights = gop_utils.get_random_block_weights([train_states['weights']['gop' + suffix],
                                                                            train_states['weights']['bn' + suffix],
                                                                            train_states['weights']['output']])

                    suffix = '_' + str(layer_iter) + '_' + str(block_iter)
                    block_names = ['gop' + suffix, 'bn' + suffix, 'output']

                    # add new block configuration
                    train_states['topology'][-2].append(('gop', params['block_size']))
                    train_states['op_set_indices']['gop' + suffix] = block_op_set_idx
                    train_states['weights']['gop' + suffix] = block_weights[0]
                    train_states['weights']['bn' + suffix] = block_weights[1]
                    train_states['weights']['output'] = block_weights[2]

                    cuda_status = misc.set_cuda_variable(
                        params['finetune_computation'][0], params['finetune_computation'][1])

                    try:
                        if verbose:
                            print('##### Block finetuning ######')
                        b_results = gop_utils.block_update(train_states['topology'],
                                                           train_states['op_set_indices'],
                                                           train_states['weights'],
                                                           params,
                                                           block_names,
                                                           train_func,
                                                           train_data,
                                                           val_func,
                                                           val_data,
                                                           test_func,
                                                           test_data)
                        new_measure, history, train_states['weights'] = b_results

                    except BaseException as error:
                        misc.reset_cuda_variable(cuda_status)
                        print(error)
                        raise RuntimeError('Fail updating block weights after randomized search')

                    misc.reset_cuda_variable(cuda_status)

                    if verbose:
                        self.print_performance(
                            history, params['convergence_measure'], params['direction'])

                    if block_iter > 0:
                        if misc.check_convergence(
                                new_measure, train_states['measure'][layer_iter][block_iter - 1],
                                params['direction'], params['block_threshold']):
                            train_states['topology'][-2].pop()
                            del train_states['weights']['gop' + suffix]
                            del train_states['weights']['bn' + suffix]
                            del train_states['op_set_indices']['gop' + suffix]
                            train_states['weights']['output'] = copy.deepcopy(
                                train_states['block_output_weight'])

                            train_states['block_iter'] = 0
                            train_states['layer_iter'] += 1
                            block_stop = True
                            path = os.path.join(params['tmp_dir'],
                                                params['model_name'], 'train_states.pickle')
                            with open(path, 'wb') as fid:
                                pickle.dump(train_states, fid)

                            break

                    train_states['block_output_weight'] = copy.deepcopy(
                        train_states['weights']['output'])
                    train_states['measure'][layer_iter].append(new_measure)
                    train_states['history'][layer_iter].append(history)
                    train_states['block_iter'] = 0 if block_iter == params['max_block'] - \
                        1 else block_iter + 1

                    path = os.path.join(params['tmp_dir'],
                                        params['model_name'], 'train_states.pickle')
                    with open(path, 'wb') as fid:
                        pickle.dump(train_states, fid)

                if layer_iter > 0:
                    if misc.check_convergence(train_states['measure'][layer_iter][-1],
                                              train_states['measure']
                                              [layer_iter - 1][-1],
                                              params['direction'],
                                              params['layer_threshold']):
                        no_blocks = len(train_states['topology'].pop(-2))
                        suffices = ['_' + str(layer_iter) + '_' + str(idx)
                                    for idx in range(no_blocks)]
                        for suffix in suffices:
                            del train_states['weights']['gop' + suffix]
                            del train_states['weights']['bn' + suffix]
                            del train_states['op_set_indices']['gop' + suffix]
                        train_states['weights']['output'] = copy.deepcopy(
                            train_states['layer_output_weight'])
                        del train_states['history'][-1]

                        break

                if not block_stop:
                    train_states['layer_iter'] += 1

                train_states['layer_output_weight'] = copy.deepcopy(
                    train_states['weights']['output'])

            train_states['is_finished'] = True
            path = os.path.join(params['tmp_dir'], params['model_name'], 'train_states.pickle')
            with open(path, 'wb') as fid:
                pickle.dump(train_states, fid)

        model_data = {'model': self.model_name,
                      'topology': train_states['topology'],
                      'op_sets': misc.map_operator_from_index(train_states['op_set_indices'],
                                                              params['nodal_set'],
                                                              params['pool_set'],
                                                              params['activation_set']),
                      'weights': train_states['weights'],
                      'use_bias': train_states['use_bias'],
                      'output_activation': train_states['output_activation']}

        self.model_data = model_data
        params['convergence_measure'] = original_convergence_measure

        return train_states['history']
