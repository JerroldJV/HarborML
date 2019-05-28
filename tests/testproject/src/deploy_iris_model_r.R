library(randomForest)

rf <- readRDS('model/iris_model_r/iris_rf.RDS')

api_predict <- function(data){
    df <- data.frame(
        Sepal.Length = data[1],
        Sepal.Width = data[2],
        Petal.Length = data[3],
        Petal.Width = data[4]
    )
    predict(rf, df)
}
