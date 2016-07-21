from py4j.java_gateway import java_import
from py4j.protocol import Py4JJavaError
from pyspark import RDD, StorageLevel
from pyspark.mllib.common import _java2py

from py_prep_buddy import py2java_int_list
from py_prep_buddy.class_names import ClassNames
from py_prep_buddy.cluster.clusters import Clusters
from py_prep_buddy.cluster.text_facets import TextFacets
from py_prep_buddy.exceptions.application_exception import ApplicationException
from py_prep_buddy.serializer import BuddySerializer
from py_prep_buddy.utils.pivot_table import PivotTable


class TransformableRDD(RDD):
    def __init__(self, rdd, file_type='CSV', t_rdd=None, sc=None):
        if rdd is not None:
            jvm = rdd.ctx._jvm
            java_import(jvm, ClassNames.BYTES_TO_STRING)
            java_import(jvm, ClassNames.TRANSFORMABLE_RDD)

            self.__set_file_type(jvm, file_type)
            self.spark_context = rdd.ctx
            java_rdd = rdd._reserialize(BuddySerializer())._jrdd.map(jvm.BytesToString())
            self._transformable_rdd = jvm.JavaTransformableRDD(java_rdd, self.__file_type)
            RDD.__init__(self, rdd._jrdd, rdd.ctx)
        else:
            jvm = sc._jvm
            java_import(jvm, ClassNames.STRING_TO_BYTES)
            self.spark_context = sc
            self.__set_file_type(jvm, file_type)
            self._transformable_rdd = t_rdd
            rdd = t_rdd.map(jvm.StringToBytes())
            RDD.__init__(self, rdd, sc, BuddySerializer())

    def __set_file_type(self, jvm, file_type):
        java_import(jvm, ClassNames.FileType)
        file_types = {
            'CSV': jvm.FileType.CSV,
            'TSV': jvm.FileType.TSV
        }
        if file_type in file_types.values():
            self.__file_type = file_type
        elif file_type.upper() in file_types:
            self.__file_type = file_types[file_type.upper()]
        else:
            raise ValueError('"%s" is not a valid file type\nValid file types are CSV and TSV' % file_type)

    def deduplicate(self, column_indexes=None):
        """
        Returns a new TransformableRDD containing only unique records by considering all the columns as the primary key.
        :param column_indexes: Sequence of the column index
        :return: TransformableRDD
        """
        if column_indexes is None:
            return TransformableRDD(None, self.__file_type, self._transformable_rdd.deduplicate(),
                                    sc=self.spark_context)
        return TransformableRDD(None, self.__file_type, self._transformable_rdd.deduplicate(column_indexes),
                                sc=self.spark_context)

    def impute(self, column_index, imputation_strategy):
        """
        Returns a new TransformableRDD by imputing missing values of the @column_index using the @imputation_strategy
        :param column_index: index of the column on which we want to impute
        :param imputation_strategy: strategy for impute the missing value
        :return: TransformableRDD
        """
        strategy_apply = imputation_strategy.get_strategy(self.spark_context)
        return TransformableRDD(None,
                                self.__file_type,
                                self._transformable_rdd.impute(column_index, strategy_apply),
                                sc=self.spark_context)

    def clusters(self, column_index, clustering_algorithm):
        """
        Returns Clusters that has all cluster of text of @columnIndex according to @clustering_algorithm
        :param column_index: index of the column
        :param clustering_algorithm: Algorithm to be used to form clusters
        :return: Clusters
        """
        algorithm = clustering_algorithm.get_algorithm(self.spark_context)
        return Clusters(self._transformable_rdd.clusters(column_index, algorithm))

    def list_facets_of(self, column_index):
        """
        Returns a new TextFacet containing the facets of @columnIndex
        :param column_index: Index of the column
        :return: TextFacets
        """
        try:
            return TextFacets(self._transformable_rdd.listFacets(column_index))
        except Py4JJavaError as e:
            java_exception = e.java_exception
            raise ApplicationException(java_exception)

    def list_facets(self, column_indexes):
        """
        Returns a new TextFacet containing the facets of @columnIndexes
        :param column_indexes: Sequence of column indexes
        :return: TextFacets
        """
        array = py2java_int_list(self.spark_context, column_indexes)
        return TextFacets(self._transformable_rdd.listFacets(array))

    def select(self, column_index, *column_indexes):
        """
        Returns RDD of given column
        :param column_index: index of the column
        :return: RDD
        """
        if column_indexes.__len__() == 0:
            return self._transformable_rdd.select(column_index)
        java_array = py2java_int_list(self.spark_context, column_indexes)
        java_array.add(0, column_index)
        java_rdd = self._transformable_rdd.select(java_array)
        return TransformableRDD(None, self.__file_type, java_rdd, sc=self.spark_context)

    def normalize(self, column_index, normalizer_strategy):
        """
        Returns a new TransformableRDD by normalizing values of the given column using different Normalizers
        :param column_index: Index of the column
        :param normalizer_strategy: normalization strategy by which you want to normalize
        :return: TransformableRDD
        """
        normalizer = normalizer_strategy.get_normalizer(self.spark_context)
        return TransformableRDD(None, self.__file_type, self._transformable_rdd.normalize(column_index, normalizer),
                                sc=self.spark_context)

    def smooth(self, column_index, smoothing_method):
        """
        Returns a new RDD containing smoothed values of @columnIndex using @smoothing_method
        :param column_index: Index of the column
        :param smoothing_method: smoothing method by which you want to smooth data
        :return: RDD
        """
        method = smoothing_method.get_smoothing_method(self.spark_context)
        rdd = self._transformable_rdd.smooth(column_index, method)
        return _java2py(self.spark_context, rdd.rdd())

    def merge_columns(self, merge_plan):
        """
        Returns a new TransformableRDD containing the merged column using @merge_plan
        :param merge_plan:
        :return: TransformableRDD
        """
        plan = merge_plan.get_plan(self.spark_context)
        return TransformableRDD(None, self.__file_type,
                                self._transformable_rdd.mergeColumns(plan),
                                sc=self.spark_context)

    def split_column(self, split_plan):
        """
        Returns a new TransformableRDD containing split columns using @split_plan
        :param split_plan: Plan specifying how to split the column
        :return: TransformableRDD
        """
        plan = split_plan.get_plan(self.spark_context)
        return TransformableRDD(None, self.__file_type,
                                self._transformable_rdd.splitColumn(plan),
                                sc=self.spark_context)

    def get_duplicates(self, column_indexes=None):
        """
        Returns a new TransformableRDD containing unique duplicate records of this TransformableRDD by considering the
        given columns as primary key.
        :param column_indexes: Sequence of column indexes
        :return: TransformableRDD
        """
        if column_indexes is None:
            return TransformableRDD(None, self.__file_type,
                                    self._transformable_rdd.duplicates(),
                                    sc=self.spark_context)
        return TransformableRDD(None, self.__file_type,
                                self._transformable_rdd.duplicates(column_indexes),
                                sc=self.spark_context)

    def drop_column(self, column_index):
        """
        Returns a new TransformableRDD by dropping the column at given index
        :param column_index: Index of the column
        :return:
        """
        return TransformableRDD(None, self.__file_type,
                                self._transformable_rdd.drop(column_index),
                                sc=self.spark_context)

    def replace_values(self, one_cluster, new_value, column_index):
        """
        Returns a new TransformableRDD by replacing the @cluster's text with specified @new_value
        :param one_cluster: Cluster of similar values to be replaced
        :param new_value: Value that will be used to replace all the cluster value
        :param column_index: Column index
        :return: TransformableRDD
        """
        cluster = one_cluster.get_cluster()
        return TransformableRDD(None, self.__file_type,
                                self._transformable_rdd.replaceValues(cluster, new_value, column_index),
                                sc=self.spark_context)

    def multiply_columns(self, first_column, second_column):
        """
        Returns a RDD which is a product of the values in @first_column and @second_column
        :param first_column: One column index
        :param second_column: Another column index
        :return: RDD
        """
        _rdd = self._transformable_rdd.multiplyColumns(first_column, second_column).rdd()
        return _java2py(self.spark_context, _rdd)

    def to_double_rdd(self, column_index):
        """
        Returns a RDD by converting values to double of given column index
        :param column_index:
        :return:
        """
        rdd = self._transformable_rdd.toDoubleRDD(column_index).rdd()
        return _java2py(self.spark_context, rdd)

    def add_columns_from(self, other):
        return TransformableRDD(None, self.__file_type,
                                self._transformable_rdd.addColumnsFrom(other._transformable_rdd),
                                sc=self.spark_context)

    def pivot_by_count(self, pivotal_column, independent_column_indexes):
        """
        Generates a PivotTable by pivoting data in the pivotalColumn
        :param pivotal_column: Pivotal column index
        :param independent_column_indexes: Independent column indexes
        :return: PivotTable
        """
        column_indexes = py2java_int_list(self.spark_context, independent_column_indexes)
        return PivotTable(self._transformable_rdd.pivotByCount(pivotal_column, column_indexes))

    def map(self, function, preservesPartitioning=False):
        return TransformableRDD(super(TransformableRDD, self).map(function, preservesPartitioning), self.__file_type)

    def filter(self, f):
        return TransformableRDD(super(TransformableRDD, self).filter(f), self.__file_type)

    def cache(self):
        return TransformableRDD(super(TransformableRDD, self).cache(), self.__file_type)

    def coalesce(self, num_partitions, shuffle=False):
        return TransformableRDD(super(TransformableRDD, self).coalesce(num_partitions, shuffle), self.__file_type)

    def distinct(self, num_partitions=None):
        return TransformableRDD(super(TransformableRDD, self).distinct(num_partitions), self.__file_type)

    def flatMap(self, func, preserves_partitioning=False):
        return TransformableRDD(super(TransformableRDD, self).flatMap(func, preserves_partitioning), self.__file_type)

    def intersection(self, other):
        return TransformableRDD(super(TransformableRDD, self).intersection(other), self.__file_type)

    def persist(self, storage_level=StorageLevel.MEMORY_ONLY_SER):
        return TransformableRDD(super(TransformableRDD, self).persist(storage_level), self.__file_type)

    def unpersist(self):
        return TransformableRDD(super(TransformableRDD, self).unpersist(), self.__file_type)

    def union(self, other):
        return TransformableRDD(super(TransformableRDD, self).union(other), self.__file_type)

    def mapPartitions(self, func, preserves_partitioning=False):
        return TransformableRDD(super(TransformableRDD, self).mapPartitions(func, preserves_partitioning),
                                self.__file_type)

    def sortBy(self, keyfunc, ascending=True, num_partitions=None):
        return TransformableRDD(super(TransformableRDD, self).sortBy(keyfunc, ascending, num_partitions),
                                self.__file_type)

    def setName(self, name):
        return TransformableRDD(super(TransformableRDD, self).setName(name), self.__file_type)

    def subtract(self, other, num_partitions=None):
        return TransformableRDD(super(TransformableRDD, self).subtract(other, num_partitions), self.__file_type)

    def subtractByKey(self, other, num_partitions=None):
        return TransformableRDD(super(TransformableRDD, self).subtractByKey(other, num_partitions), self.__file_type)

    def sample(self, with_replacement, fraction, seed=None):
        return TransformableRDD(super(TransformableRDD, self).sample(with_replacement, fraction, seed),
                                self.__file_type)

    def repartition(self, num_partitions):
        return TransformableRDD(super(TransformableRDD, self).repartition(num_partitions), self.__file_type)

    def pipe(self, command, env=None, check_code=False):
        return TransformableRDD(super(TransformableRDD, self).pipe(command, env, check_code), self.__file_type)
