#!/bin/csh -f
# 敏感性实验 B：Pangu 默认气象场，仅把 CMAQ 的 KZMIN 改为 KZ0UT（=1.0 m2/s）
setenv LD_LIBRARY_PATH /usr/local/lib
setenv DIR /home/ubuntu01/sda/AI2MCIP/Pangu_AQF/CMAQv5.2/Build_MODEL
setenv PATH $DIR/netcdf/bin:$PATH
setenv PATH $DIR/mpich/bin:$PATH
setenv LD_LIBRARY_PATH $DIR/netcdf/lib:$LD_LIBRARY_PATH
setenv LD_LIBRARY_PATH $DIR/mpich/lib:$LD_LIBRARY_PATH
setenv LD_LIBRARY_PATH $DIR/grib2/lib:$LD_LIBRARY_PATH
setenv compiler gcc

setenv DomainName        ECPGV3_KZ1
setenv MODEL_HOME        /home/ubuntu01/sda/AI2MCIP/Pangu_AQF
setenv CMAQHOME          ${MODEL_HOME}/CMAQv5.2
setenv MIDDLE_DATA       ${MODEL_HOME}/MIDDLE_DATA
setenv LOGD              ${MODEL_HOME}/logs_v2
setenv START_DAY         2025-10-27
setenv ENDDD_DAY         2025-11-04
setenv course            16
setenv course_camx       16
setenv model             camx

source ${MODEL_HOME}/run_scripts/config.wrf.camx.smoke.test
source ${CMAQHOME}/config_cmaq.csh $compiler

setenv CMAQ_SH ${MODEL_HOME}/run_scripts/sub_scripts/cmaq/d01_CSH
tcsh /home/ubuntu01/sda/AI2MCIP/paper/scripts/run_cctm_kz1.csh
