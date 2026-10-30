#!/bin/csh -f
# 补跑 FengYuan 分支 CCTM（2025-10-27 .. 2025-11-04，共 9 天）
# 仅调用 CMAQ CCTM + COMBINE，不改动其他分支任何文件
setenv LD_LIBRARY_PATH /usr/local/lib
setenv DIR /home/ubuntu01/sda/AI2MCIP/Fengyuan_AQF/CMAQv5.2/Build_MODEL
setenv PATH $DIR/netcdf/bin:$PATH
setenv PATH $DIR/mpich/bin:$PATH
setenv LD_LIBRARY_PATH /usr/local/cuda/targets/x86_64-linux/lib:$LD_LIBRARY_PATH
setenv LD_LIBRARY_PATH $DIR/netcdf/lib:$LD_LIBRARY_PATH
setenv LD_LIBRARY_PATH $DIR/mpich/lib:$LD_LIBRARY_PATH
setenv LD_LIBRARY_PATH $DIR/grib2/lib:$LD_LIBRARY_PATH
setenv compiler gcc

setenv START_DAY         2025-10-26
setenv ENDDD_DAY         `date -ud "${START_DAY} +9day" +%Y-%m-%d`
setenv DomainName        ECPGV3_$START_DAY
setenv course_camx       16
setenv course            16
setenv model             camx
setenv MODEL_HOME        /home/ubuntu01/sda/AI2MCIP/Fengyuan_AQF
setenv CMAQHOME          ${MODEL_HOME}/CMAQv5.2
setenv PYTHON            ~/miniconda3/bin/python
setenv MIDDLE_DATA       ${MODEL_HOME}/MIDDLE_DATA
setenv LOGD              ${MODEL_HOME}/logs_v2

source ${MODEL_HOME}/run_scripts/config.wrf.camx.smoke.test
source ${CMAQHOME}/config_cmaq.csh $compiler

set dom = "01"
setenv CMAQ_SH ${MODEL_HOME}/run_scripts/sub_scripts/cmaq/d${dom}_CSH
setenv START_DAY    `date -ud "${START_DAY} +1 day" +%Y-%m-%d`

tcsh ${CMAQ_SH}/run_cctm_d${dom}.csh
tcsh ${CMAQ_SH}/run_combine_d${dom}.csh
