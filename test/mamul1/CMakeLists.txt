
enable_language (Fortran)

set(MAMUL1_USE_MAGMA "OFF" CACHE BOOL "if set, mamul1 build uses magma (matrix algebra on gpu)")

set(MAMUL1_MAGMA_API "CPU_MEM_API" CACHE STRING "which magma API to use when building mamul1: CPU_MEM_API for BLAS compatible API (uses matrices stored on CPU memory) or GPU_MEM_API (use matrices stored on GPU memory)")

add_executable(mamul1 mamul1.F90)

if (CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
	# Allow arbitrary long lines. Needed as preprocessing could generate long line lengths.
	target_compile_options(mamul1 PUBLIC -ffree-line-length-none)
elseif (Fortran_COMPILER_NAME STREQUAL "ifort")
	# Intel (ifort)
	target_compile_options(mamul1 PUBLIC -no-wrap-margin)
endif()


if (MAMUL1_USE_MAGMA)
	find_package( MAGMA REQUIRED )
	if( MAMUL1_MAGMA_API STREQUAL "CPU_MEM_API" )
		target_compile_definitions(mamul1 PUBLIC USE_MAGMA_DGEMM)
	elseif( MAMUL1_MAGMA_API STREQUAL "GPU_MEM_API" )
		target_compile_definitions(mamul1 PUBLIC USE_MAGMA_DGEMM_GPU)
	else()
		message(FATAL_ERROR "unexpected value for MAMUL1_MAGMA_API : ${MAMUL1_MAGMA_API}")
	endif()
	message(STATUS "MAGMA_INCLUDES=${MAGMA_INCLUDES}")
	include_directories("${MAGMA_INCLUDES}")
	target_link_libraries(mamul1 "${MAGMA_LIBRARIES}")
else()
	find_package( BLAS REQUIRED )
	find_package( LAPACK REQUIRED )
	# message("BLAS_LIBRARIES=${BLAS_LIBRARIES}")
	# message("LAPACK_LIBRARIES=${LAPACK_LIBRARIES}")
	target_compile_definitions(mamul1 PUBLIC USE_DGEMM)

	# Link Blas and Lapack libraries
	target_link_libraries(mamul1 "${LAPACK_LIBRARIES}")
	target_link_libraries(mamul1 "${BLAS_LIBRARIES}")
endif()

install(TARGETS mamul1)
