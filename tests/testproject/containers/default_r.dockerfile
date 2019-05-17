FROM r-base
RUN R -e "install.packages(c('plumber', 'randomForest'))"
