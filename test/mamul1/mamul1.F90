#define MAMUL1_VERSION "1.0.0"

#define magma_devptr_t integer(kind=8)
subroutine print_usage(prog_path)
    character(len=*), intent(in) :: prog_path
    character(len=80) :: build_variant
#if defined(USE_MAGMA_DGEMM_GPU)
    build_variant='gpu'
#elif defined(USE_DGEMM)
    build_variant='cpu'
#else
    build_variant='unknown'
#endif
    write(6,'("mamul1 v",a," (variant:",a,"): benchmark performs a square matrix multiplication in double precision")') MAMUL1_VERSION, trim(build_variant);
    write(6,'()');
    write(6,'("Usage: ",a," <NDIM> <NUM_LOOPS>")') trim(prog_path);
    write(6,'("   <NDIM> positive integer representing the size of the square matrices to multiply ")');
    write(6,'("   <NUM_LOOPS> positive integer representing the number of times the multiplication is performed")');
end subroutine

program mamul1

implicit none


integer :: argc, info, ndim, num_loops

character(len=32) :: arg0, arg1, arg2


call get_command_argument(0,arg0)

argc = command_argument_count()
if (argc /= 2) then
    call print_usage(trim(arg0))
    ! write(6,'("Usage: ",a," NDIM NUM_LOOPS, where NDIM is a positive integer")') trim(arg0);
    stop
end if

call get_command_argument(1,arg1,status=info)
if (info /= 0) then
    write(6,'("Error reading argument: info = ",i2)') info
    call print_usage(trim(arg0))
stop
end if

call get_command_argument(2,arg2,status=info)
if (info /= 0) then
    write(6,'("Error reading argument: info = ",i2)') info
    call print_usage(trim(arg0))
stop
end if

read(arg1,*,iostat=info) ndim
if (info /= 0) then
    write(6,'("Error converting ndim argument to integer: info = ",i2)') info
    call print_usage(trim(arg0))
stop
end if

read(arg2,*,iostat=info) num_loops
if (info /= 0) then
    write(6,'("Error converting num_loops argument to integer: info = ",i2)') info
    call print_usage(trim(arg0))
stop
end if


if (ndim < 1) then
    call print_usage(trim(arg0))
stop
end if

    call test_dgemm(ndim, num_loops)

stop
end program mamul1

subroutine set_random_seed(seed)
    integer :: seed
    integer :: seed_array_size
    INTEGER, ALLOCATABLE :: seed_array (:)
    CALL RANDOM_SEED (SIZE = seed_array_size)  ! I is set to the size of
    !                              ! the seed array
    ALLOCATE (seed_array(seed_array_size))
    seed_array = seed
    CALL RANDOM_SEED (PUT=seed_array(1:seed_array_size))
end subroutine

subroutine print_matrix(mat, ndim)
    implicit none
    integer, parameter :: dp = kind(1.0d0)
    real(dp), intent(in) :: mat(ndim, ndim)
    integer, intent(in) :: ndim
    integer :: irow
    do irow = 1, ndim
        write(6, *) mat(irow,:)
    end do
end subroutine

! square matrix multiplication
subroutine sqmatmul(amat, bmat, cmat, ndim)
#if defined(USE_MAGMA_DGEMM_GPU)
    use magma, only: magmaf_init, magmaf_finalize
    use magma, only: magmaf_queue_create, magmaf_queue_destroy
    use magma, only: magmaf_dmalloc, magmaf_free
    use magma, only: magmaf_dsetmatrix, magmaf_dgetmatrix
    use magma, only: magmablasf_dgemm
#endif
    real*8, intent(in) :: amat(ndim,ndim)
    real*8, intent(in) :: bmat(ndim,ndim)
    real*8, intent(out) :: cmat(ndim,ndim)
    integer :: lda, ldb, ldc
    integer :: info

    real :: time_before, time_after
    integer(8) :: num_ops
    real :: gflops

#ifdef USE_MAGMA_DGEMM_GPU
    magma_devptr_t :: d_amat
    magma_devptr_t :: d_bmat
    magma_devptr_t :: d_cmat
    magma_devptr_t :: queue  !! really a CPU pointer
#endif
    lda = ceiling(real(ndim)/32)*32
    ldb = ceiling(real(ndim)/32)*32
    ldc = ceiling(real(ndim)/32)*32


#if defined(USE_MAGMA_DGEMM_GPU)
    !! allocate GPU memory
    write(6,'("DEBUG: before matrix A gpu memory allocation (",i0," doubles)")') lda * ndim
    info = magmaf_dmalloc( d_amat, lda*ndim )
    if (d_amat == 0) then
        print "(a)", "failed to allocate d_amat"
        return
    endif
    write(6,'("DEBUG: before matrix B gpu memory allocation (",i0," doubles)")') ldb * ndim
    info = magmaf_dmalloc( d_bmat, ldb*ndim )
    if (d_bmat == 0) then
        print "(a)", "failed to allocate d_bmat"
        return
    endif
    write(6,'("DEBUG: before matrix C gpu memory allocation (",i0," doubles)")') ldc * ndim
    info = magmaf_dmalloc( d_cmat, ldc*ndim )
    if (d_cmat == 0) then
        print "(a)", "failed to allocate d_cmat"
        return
    endif

    ! copy A to dA and B to dB
    call magmaf_queue_create( 0, queue )
    write(6,'("DEBUG: queue = ",i0)') queue
    if (queue == 0) then
        print "(a)", "failed to create a queue"
        return
    endif

    write(6,*) 'DEBUG: copying matrix A from CPU to GPU memory'
    call magmaf_dsetmatrix( ndim, ndim, amat, ndim, d_amat, lda, queue )
    write(6,*) 'DEBUG: copying matrix B from CPU to GPU memory'
    call magmaf_dsetmatrix( ndim, ndim, bmat, ndim, d_bmat, ldb, queue )

    call cpu_time(time_before)
    write (6,*) 'before magmablasf_dgemm, time=', time_before

    call magmablasf_dgemm ('N', 'N', ndim, ndim, ndim, 1.0d0, d_amat, lda, d_bmat, ldb, 0.0d0, d_cmat, ldc, queue)
    call magmaf_queue_sync(queue)

    call cpu_time(time_after)
    num_ops = real(ndim) * real(ndim) * real(ndim) * 2
    gflops = num_ops / (time_after - time_before) / 1.0e9
    write (6,*) 'after magmablasf_dgemm, time=', time_after
    write (6,*) 'magmablasf_dgemm (from gpu memory to gpu memory) duration :', (time_after - time_before), '(', gflops, ' gflops)'

    write(6,*) 'DEBUG: copying matrix C from GPU to CPU memory'
    call magmaf_dgetmatrix( ndim, ndim, d_cmat, ldc, cmat, ndim, queue )
    call magmaf_queue_destroy( queue )

    info = magmaf_free(d_cmat)
    info = magmaf_free(d_bmat)
    info = magmaf_free(d_amat)

#endif

#ifdef USE_DGEMM
    ! subroutine dgemm 	( 	character  	TRANSA,
    ! 		character  	TRANSB,
    ! 		integer  	M,
    ! 		integer  	N,
    ! 		integer  	K,
    ! 		double precision  	ALPHA,
    ! 		double precision, dimension(lda,*)  	A,
    ! 		integer  	LDA,
    ! 		double precision, dimension(ldb,*)  	B,
    ! 		integer  	LDB,
    ! 		double precision  	BETA,
    ! 		double precision, dimension(ldc,*)  	C,
    ! 		integer  	LDC 
    ! 	) 	        
    call dgemm('N', 'N', ndim, ndim, ndim, 1.0d0, amat, ndim, bmat, ndim, 0.0d0, cmat, ndim)
#endif

end subroutine

subroutine check_cmat_element(cmat, row, col, amat, bmat, ndim)
    real(8), intent(in) :: cmat(ndim, ndim)
    integer, intent(in) :: row
    integer, intent(in) :: col
    real(8), intent(in) :: amat(ndim, ndim)
    real(8), intent(in) :: bmat(ndim, ndim)
    integer, intent(in) :: ndim

    real(8) :: x
    x = 0.0d0
    do i = 1, ndim
       x = x + amat(row, i) * bmat(i, col)
    end do

    write(6, '("expected cmat(", i0, ", ", i0, ")", e23.15e3)') row, col, x
    write(6, '("computed cmat(", i0, ", ", i0, ")", e23.15e3)') row, col, cmat(row, col)
    if (abs(cmat(row, col) - x) > 1.0e-8) then
        stop 'a computed element has a wrong value'
    end if
end subroutine


subroutine test_dgemm(ndim, num_loops)
#if defined(USE_MAGMA_DGEMM_GPU)
    use magma, only: magmaf_init, magmaf_finalize
    use magma, only: magmablasf_dgemm  !, magmaf_dgemm_gpu
#endif

    implicit none
    integer, intent(in) :: ndim
    integer, intent(in) :: num_loops
    integer, parameter :: dp = kind(1.0d0)
    real :: tstart, tstop
    integer(8) :: num_ops
    real :: gflops

    INTEGER :: c1,c2,cr,cm,s
    REAL :: a_diff, diff, rate

    real*8, allocatable :: amat(:,:)
    real*8, allocatable :: bmat(:,:)
    real*8, allocatable :: cmat(:,:)
    real(dp) :: x
    integer :: i, j

#if defined(USE_MAGMA_DGEMM_GPU)
    write(6,*) 'DEBUG: init magma'
    call magmaf_init()
#endif

    ! First initialize the system_clock
    CALL system_clock(count_rate=cr)
    CALL system_clock(count_max=cm)
    rate = REAL(cr)
    WRITE(*,*) "system_clock rate ",rate

    diff = 0.0
    a_diff = 0.0
    s = 0

    allocate(amat(ndim, ndim))
    allocate(bmat(ndim, ndim))
    allocate(cmat(ndim, ndim))

    call set_random_seed(42)

    !call random_number(amat)
    !amat = 0.5_dp*(amat + transpose(amat))
    do j = 1, ndim
        do i = 1, ndim
           call random_number(x)
           amat(i,j) = x
           call random_number(x)
           bmat(i,j) = x
        end do
    end do

    call cpu_time(tstart)
    call system_clock(c1)

    do j = 1, num_loops
        ! playmat = amat

        call sqmatmul(amat, bmat, cmat, ndim)

    end do

    call cpu_time(tstop)
    call system_clock(c2)
    if ( (c2 - c1)/rate < (tstop - tstart) ) s = s + 1
    diff = (c2 - c1)/rate - (tstop - tstart) + diff
    a_diff = ABS((c2 - c1)/rate - (tstop - tstart)) + a_diff

    ! check one of the elements of cmat (the last one here: cmat(ndim, ndim))
    call check_cmat_element(cmat,    1,    1, amat, bmat, ndim)
    call check_cmat_element(cmat,    1, ndim, amat, bmat, ndim)
    call check_cmat_element(cmat, ndim,    1, amat, bmat, ndim)
    call check_cmat_element(cmat, ndim, ndim, amat, bmat, ndim)

    ! write(6, *) 'amat = '
    ! call print_matrix(amat, ndim)

    ! write(6, *) 'bmat = '
    ! call print_matrix(bmat, ndim)

    ! write(6, *) 'cmat = '
    ! call print_matrix(cmat, ndim)

    num_ops = real(ndim) * real(ndim) * real(ndim) * 2 * num_loops
    gflops = num_ops / (tstop-tstart) / 1.0e9


    write(6, '("Time taken by dgemm for matrix size ",i8," was ",f10.2," seconds")') ndim, tstop-tstart
    WRITE(*,*) "gflops (from cpu memory to cpu memory)       : ", gflops
    
    WRITE(*,*) "system_clock : ",(c2 - c1)/rate
    WRITE(*,*) "cpu_time     : ",(tstop - tstart)
    WRITE(*,*) "sc < ct      : ",s
    WRITE(*,*) "mean diff    : ",diff
    WRITE(*,*) "abs mean diff: ",a_diff

#if defined(USE_MAGMA_DGEMM_GPU)
    write(6,*) 'DEBUG: deinit magma'
    call magmaf_finalize()
#endif


    deallocate(amat, bmat, cmat)
    end
