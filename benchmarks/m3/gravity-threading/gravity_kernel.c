#define _GNU_SOURCE
#include <math.h>
#include <mpi.h>
#include <omp.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef _OPENMP
#error Compile this benchmark with OpenMP enabled.
#endif

enum { WIDTH = 4, TILE = 4, SAMPLES = 7 };
static int n, first, local_n;
static double softening2, *source, *out;

extern int rayon_team_init(int threads);
extern void rayon_force_tiles(int tiles);

static void fail(const char *message) {
    fprintf(stderr, "gravity benchmark: %s\n", message);
    MPI_Abort(MPI_COMM_WORLD, 2);
    abort();
}

static void *allocate(size_t count, size_t element) {
    void *p = calloc(count ? count : 1, element);
    if (!p) fail("allocation");
    return p;
}

typedef struct { double sum, correction; } Sum;

static inline void add(Sum *s, double x) {
    double next = s->sum + x;
    s->correction += fabs(s->sum) >= fabs(x) ? (s->sum - next) + x : (x - next) + s->sum;
    s->sum = next;
}

/* Both schedulers invoke this single compiled function. One target owns its total. */
void gravity_tile(int tile) {
    int end = (tile + 1) * TILE;
    if (end > local_n) end = local_n;
    for (int local = tile * TILE; local < end; ++local) {
        int i = first + local;
        const double *a = source + WIDTH * i;
        Sum force[3] = {{0}}, phi = {0};
        for (int j = 0; j < n; ++j) {
            if (i == j) continue;
            const double *b = source + WIDTH * j;
            double d[3] = {b[1] - a[1], b[2] - a[2], b[3] - a[3]};
            Sum dot = {0};
            for (int axis = 0; axis < 3; ++axis) add(&dot, d[axis] * d[axis]);
            double s2 = (dot.sum + dot.correction) + softening2;
            double s = sqrt(s2);
            double coefficient = (a[0] * b[0]) / (s2 * s);
            for (int axis = 0; axis < 3; ++axis) add(force + axis, d[axis] * coefficient);
            add(&phi, -b[0] / s);
        }
        for (int axis = 0; axis < 3; ++axis)
            out[WIDTH * local + axis] = (force[axis].sum + force[axis].correction) / a[0];
        out[WIDTH * local + 3] = phi.sum + phi.correction;
    }
}

static void evaluate(int openmp, int threads) {
    int tiles = (local_n + TILE - 1) / TILE;
    if (openmp) {
        int actual = 0;
        #pragma omp parallel num_threads(threads) shared(actual)
        {
            #pragma omp single nowait
            actual = omp_get_num_threads();
            #pragma omp for schedule(static)
            for (int tile = 0; tile < tiles; ++tile) gravity_tile(tile);
        }
        if (actual != threads) fail("OpenMP team size");
    } else {
        rayon_force_tiles(tiles);
    }
}

/* Both runtimes inherit identical disjoint logical-CPU sets on a single node. */
static void place_rank(int rank, int ranks, int threads) {
    cpu_set_t available, used, assigned;
    if (sched_getaffinity(0, sizeof available, &available)) fail("read CPU affinity");
    cpu_set_t *masks = allocate((size_t)ranks, sizeof *masks);
    MPI_Allgather(&available, (int)sizeof available, MPI_BYTE, masks, (int)sizeof available,
                  MPI_BYTE, MPI_COMM_WORLD);
    CPU_ZERO(&used);
    for (int r = 0; r <= rank; ++r) {
        CPU_ZERO(&assigned);
        int count = 0;
        for (int k = 0; k < CPU_SETSIZE && count < threads; ++k) {
            if (CPU_ISSET(k, &masks[r]) && !CPU_ISSET(k, &used)) {
                CPU_SET(k, &assigned);
                CPU_SET(k, &used);
                ++count;
            }
        }
        if (count != threads) fail("insufficient disjoint logical CPUs");
    }
    free(masks);
    if (sched_setaffinity(0, sizeof assigned, &assigned)
        || sched_getaffinity(0, sizeof available, &available) || !CPU_EQUAL(&assigned, &available))
        fail("apply rank CPU affinity");
    for (int r = 0; r < ranks; ++r) {
        MPI_Barrier(MPI_COMM_WORLD);
        if (r == rank) {
            printf("placement rank=%d cpus=",rank);
            int printed = 0;
            for (int k = 0; k < CPU_SETSIZE; ++k)
                if (CPU_ISSET(k,&available)) printf("%s%d",printed++ ? "," : "",k);
            printf("\n");
            fflush(stdout);
        }
    }
    MPI_Barrier(MPI_COMM_WORLD);
}

static void read_catalog(const char *file) {
    FILE *f = fopen(file,"r");
    if (!f || fscanf(f,"%d",&n) != 1 || n < 2 || n > 32768) fail("catalogue count");
    source = allocate((size_t)n * WIDTH, sizeof *source);
    for (int i = 0; i < n; ++i) {
        double *v = source + i*WIDTH;
        int id = -1;
        if (fscanf(f,"%d%lf%lf%lf%lf",&id,v,v+1,v+2,v+3) != 5 || id != i
            || !(v[0] > 0) || !isfinite(v[0]) || !isfinite(v[1]) || !isfinite(v[2]) || !isfinite(v[3]))
            fail("catalogue row");
    }
    char extra;
    if (fscanf(f," %c",&extra) != EOF || ferror(f)) fail("extra or unreadable catalogue rows");
    fclose(f);
}

int main(int argc, char **argv) {
    int provided, rank, ranks;
    MPI_Init_thread(&argc,&argv,MPI_THREAD_FUNNELED,&provided);
    MPI_Comm_rank(MPI_COMM_WORLD,&rank);
    MPI_Comm_size(MPI_COMM_WORLD,&ranks);
    MPI_Comm shared;
    MPI_Comm_split_type(MPI_COMM_WORLD,MPI_COMM_TYPE_SHARED,rank,MPI_INFO_NULL,&shared);
    int on_node;
    MPI_Comm_size(shared,&on_node);
    MPI_Comm_free(&shared);
    if (provided < MPI_THREAD_FUNNELED || on_node != ranks || argc != 6)
        fail("requires one node; arguments: openmp|rayon threads catalogue epsilon evaluations");
    int openmp = strcmp(argv[1],"openmp")==0;
    if (!openmp && strcmp(argv[1],"rayon")) fail("unknown threading runtime");
    int threads = atoi(argv[2]), batch = atoi(argv[5]);
    double eps = strtod(argv[4],NULL);
    if (threads < 1 || threads > 256 || batch < 1 || batch > 1024 || !isfinite(eps) || !(eps > 0))
        fail("invalid threads, batch or softening");
    softening2 = eps*eps;
    place_rank(rank,ranks,threads);
    if (openmp) {
        omp_set_dynamic(0);
    } else if (rayon_team_init(threads) != threads) {
        fail("Rayon team size");
    }
    if (rank == 0) read_catalog(argv[3]);
    MPI_Bcast(&n,1,MPI_INT,0,MPI_COMM_WORLD);
    if (rank != 0) source = allocate((size_t)n * WIDTH,sizeof *source);
    MPI_Bcast(source,n*WIDTH,MPI_DOUBLE,0,MPI_COMM_WORLD);
    first = n*rank/ranks;
    local_n = n*(rank+1)/ranks-first;
    out = allocate((size_t)local_n*WIDTH,sizeof *out);
    int *counts = allocate((size_t)ranks,sizeof *counts), *offsets = allocate((size_t)ranks,sizeof *offsets);
    for (int r=0; r<ranks; ++r) {
        offsets[r] = (n*r/ranks)*WIDTH;
        counts[r] = (n*(r+1)/ranks)*WIDTH-offsets[r];
    }
    size_t words = (size_t)n*WIDTH;
    double *full = rank==0 ? allocate(words,sizeof *full) : NULL;
    double *first_output = rank==0 ? allocate(words,sizeof *first_output) : NULL;
    FILE *timing = rank==0 ? fopen("timings.csv","w") : NULL;
    if (rank==0) {
        if (!timing) fail("timing output");
        fprintf(timing,"sample,stage_seconds,kernel_seconds\n");
        printf("runtime=%s ranks=%d threads=%d openmp_macro=%d particles=%d batch=%d\n",
               argv[1],ranks,threads,_OPENMP,n,batch);
    }
    for (int sample=-1; sample<SAMPLES; ++sample) {
        int iterations = sample < 0 ? 1 : batch;
        MPI_Barrier(MPI_COMM_WORLD);
        double begin = MPI_Wtime(), kernel = 0.0;
        for (int k=0; k<iterations; ++k) {
            double start_kernel = MPI_Wtime();
            evaluate(openmp,threads);
            kernel += MPI_Wtime()-start_kernel;
            MPI_Gatherv(out,local_n*WIDTH,MPI_DOUBLE,full,counts,offsets,MPI_DOUBLE,0,MPI_COMM_WORLD);
        }
        double local[2] = {(MPI_Wtime()-begin)/iterations,kernel/iterations}, maxima[2];
        MPI_Reduce(local,maxima,2,MPI_DOUBLE,MPI_MAX,0,MPI_COMM_WORLD);
        if (rank==0) {
            if (sample < 0) memcpy(first_output,full,words*sizeof *full);
            else {
                if (memcmp(first_output,full,words*sizeof *full)) fail("non-reproducible repeated force");
                fprintf(timing,"%d,%.17g,%.17g\n",sample,maxima[0],maxima[1]);
            }
        }
    }
    if (rank==0) {
        if (fclose(timing)) fail("write timings");
        FILE *f = fopen("forces.csv","w");
        if (!f) fail("force output");
        fprintf(f,"id,ax,ay,az,phi\n");
        for (int i=0; i<n; ++i) {
            const double *v = full+WIDTH*i;
            fprintf(f,"%d,%.17g,%.17g,%.17g,%.17g\n",i,v[0],v[1],v[2],v[3]);
        }
        if (fclose(f)) fail("write forces");
    }
    free(first_output); free(full); free(counts); free(offsets); free(source); free(out);
    MPI_Finalize();
    return 0;
}
