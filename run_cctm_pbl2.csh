#!/bin/csh -f
# 敏感性实验 A2 的 CCTM 段（DomainName=ECPGV3_PBL2，PBLH 仅 Richardson 数法）
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
setenv LOGD              ${MODEL_HOME}/logs_v2
setenv START_DAY         2025-10-27
setenv ENDDD_DAY         2025-11-04
setenv course            16
setenv course_camx       16
setenv model             camx

source ${MODEL_HOME}/run_scripts/config.wrf.camx.smoke.test
source ${CMAQHOME}/config_cmaq.csh $compiler

setenv CMAQ_SH ${MODEL_HOME}/run_scripts/sub_scripts/cmaq/d01_CSH
tcsh ${CMAQ_SH}/run_cctm_d01.csh
tcsh ${CMAQ_SH}/run_combine_d01.csh
