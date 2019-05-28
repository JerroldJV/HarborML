#install.packages('randomForest', repos="https://cran.cnr.berkeley.edu")
library(randomForest)

data(iris)

rf <- randomForest(Species ~ Sepal.Length + Sepal.Width + Petal.Length + Petal.Width, data = iris)

saveRDS(rf, 'output/iris_rf.RDS')