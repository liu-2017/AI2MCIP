#!/bin/csh -f
# 敏感性实验 A2：PBLH 只用 Richardson 数法（关闭对流 encroachment 分支）
# 伪 wrfout 已由 paper/scripts/pangu2wrf_a2.py 生成；此处只跑 MCIP（10-27..11-04）
setenv LD_LIBRARY_PATH /usr/local/lib
setenv DIR /home/ubuntu01/sda/AI2MCIP/Pangu_AQF/CMAQv5.2/Build_MODEL
setenv PATH $DIR/netcdf/bin:$PATH
setenv PATH $DIR/mpich/bin:$PATH
setenv LD_LIBRARY_PATH $DIR/netcdf/lib:$LD_LIBRARY_PATH
setenv LD_LIBRARY_PATH $DIR/mpich/lib:$LD_LIBRARY_PATH
setenv LD_LIBRARY_PATH $DIR/grib2/lib:$LD_LIBRARY_PATH
setenv compiler gcc

setenv DomainName        ECPGV3_PBL2
setenv MODEL_HOME        /home/ubuntu01/sda/AI2MCIP/Pangu_AQF
setenv CMAQHOME          ${MODEL_HOME}/CMAQv5.2
setenv MIDDLE_DATA       ${MODEL_HOME}/MIDDLE_DATA
setenv START_DAY         2025-10-27
setenv ENDDD_DAY         2025-11-04
setenv course            16

source ${MODEL_HOME}/run_scripts/config.wrf.camx.smoke.test
source ${CMAQHOME}/config_cmaq.csh $compiler

setenv CMAQ_SH ${MODEL_HOME}/run_scripts/sub_scripts/cmaq/d01_CSH
tcsh ${CMAQ_SH}/run.mcip.d01.csh
