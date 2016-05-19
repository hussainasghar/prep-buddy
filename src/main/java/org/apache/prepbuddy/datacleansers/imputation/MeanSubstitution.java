package org.apache.prepbuddy.datacleansers.imputation;

import org.apache.prepbuddy.rdds.TransformableRDD;
import org.apache.prepbuddy.utils.RowRecord;
import org.apache.spark.api.java.JavaDoubleRDD;

public class MeanSubstitution implements ImputationStrategy {

    private Double mean;

    @Override
    public void prepareSubstitute(TransformableRDD rdd, int columnIndex) {
        JavaDoubleRDD javaDoubleRDD = rdd.toDoubleRDD(columnIndex);
        mean = javaDoubleRDD.mean();
    }

    @Override
    public String handleMissingData(RowRecord record) {
        return mean.toString();
    }
}