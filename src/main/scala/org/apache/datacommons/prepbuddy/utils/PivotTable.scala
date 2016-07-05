package org.apache.datacommons.prepbuddy.utils

import scala.collection.{mutable}

class PivotTable[T](defaultValue: T) {

    private var lookUpTable: mutable.Map[String, mutable.Map[String, T]] = {
        new mutable.HashMap[String, mutable.Map[String, T]]()
    }

    def transform(transformedFunction: (Any) => Any, defValue: Any): Any = {
        val table = new PivotTable[Any](defValue)
        lookUpTable.foreach((rowTuple) => {
            rowTuple._2.foreach((columnTuple) => {
                table.addEntry(rowTuple._1, columnTuple._1, transformedFunction(columnTuple._2))
            })
        })
        table
    }


    def valueAt(rowKey: String, columnKey: String): T = {
        lookUpTable(rowKey)(columnKey)
    }

    def addEntry(rowKey: String, columnKey: String, value: T): Unit = {
        if (!lookUpTable.contains(rowKey)) {
            val columnMap = new mutable.HashMap[String, T]().withDefaultValue(defaultValue)
            lookUpTable += (rowKey -> columnMap)
        }
        lookUpTable(rowKey) += (columnKey -> value)
    }


}
