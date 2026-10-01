/* selfgen_img.c - NitrOS-9 native boot image builder for deep65280
 *
 * Packs kernel and system modules into a 64KB boot image file
 * matching the layout of recipes/deep65280/build_img.py
 *
 * Compiled with: cmoc --os9 -o selfgen_img selfgen_img.c
 */

#include <cmoc.h>

typedef unsigned char byte;
typedef unsigned char errnum;

asm errnum Os9Create(const char *path, int mode, int attrs, int *pathOut) {
    asm {
        pshs y,u
        ldx 6,s         ; path
        lda 9,s         ; mode
        ldb 11,s        ; attrs
        swi2
        fcb $83         ; I$Create
        bcs CrErr
        ldx 12,s        ; pathOut
        sta 1,x
        clr ,x
        clra
        clrb
        puls y,u,pc
CrErr
        clra            ; error code in B
        puls y,u,pc
    }
}

asm errnum Os9Open(const char *path, int mode, int *pathOut) {
    asm {
        pshs y,u
        ldx 6,s         ; path
        lda 9,s         ; mode
        swi2
        fcb $84         ; I$Open
        bcs OpErr
        ldx 10,s        ; pathOut
        sta 1,x
        clr ,x
        clra
        clrb
        puls y,u,pc
OpErr
        clra
        puls y,u,pc
    }
}

asm errnum Os9Delete(const char *path) {
    asm {
        pshs y,u
        ldx 6,s         ; path
        swi2
        fcb $87         ; I$Delete
        bcs DelErr
        clra
        clrb
        puls y,u,pc
DelErr
        clra
        puls y,u,pc
    }
}

asm errnum Os9Close(int path) {
    asm {
        pshs y,u
        lda 7,s         ; path
        swi2
        fcb $8F         ; I$Close
        bcs ClErr
        clra
        clrb
        puls y,u,pc
ClErr
        clra
        puls y,u,pc
    }
}

asm errnum Os9Read(int path, void *buf, int count, int *actualOut) {
    asm {
        pshs y,u
        lda 7,s         ; path
        ldx 8,s         ; buf
        ldy 10,s        ; count
        swi2
        fcb $89         ; I$Read
        bcs RdErr
        ldx 12,s        ; actualOut
        sty ,x
        clra
        clrb
        puls y,u,pc
RdErr
        clra
        puls y,u,pc
    }
}

asm errnum Os9Write(int path, const void *buf, int count, int *actualOut) {
    asm {
        pshs y,u
        lda 7,s         ; path
        ldx 8,s         ; buf
        ldy 10,s        ; count
        swi2
        fcb $8A         ; I$Write
        bcs WrErr
        ldx 12,s        ; actualOut
        sty ,x
        clra
        clrb
        puls y,u,pc
WrErr
        clra
        puls y,u,pc
    }
}

asm errnum Os9Seek(int path, unsigned int offset_hi, unsigned int offset_lo) {
    asm {
        pshs y,u
        lda 7,s         ; path
        ldx 8,s         ; offset_hi (X)
        ldu 10,s        ; offset_lo (U)
        swi2
        fcb $88         ; I$Seek
        bcs SkErr
        clra
        clrb
        puls y,u,pc
SkErr
        clra
        puls y,u,pc
    }
}

#define KRN_START_ADDR 0xEE00U

/* Module list per slot group */
const char *slot4_mods[] = { "dir", "setime", "date", "stop", NULL };
const char *slot5_mods[] = { "scf", "sc6850", "clock", "term", "shell_21", "mfree", "free", "procs", "mdir", NULL };
const char *slot6_mods[] = { "dd", "emudsk", "sysgo", "rbf", "ioman", NULL };
const char *slot7_mods[] = { "init", "krnp2", NULL };

struct SlotGroup {
    unsigned int start_addr;
    unsigned int end_addr;
    const char **mods;
};

struct SlotGroup slot_groups[] = {
    { 0x8000U, 0xA000U, slot4_mods },
    { 0xA000U, 0xC000U, slot5_mods },
    { 0xC000U, 0xE000U, slot6_mods },
    { 0xE000U, KRN_START_ADDR, slot7_mods },
    { 0, 0, NULL }
};

static char path_buf[128];
static char io_buf[512];

/* Make path: dir/name */
void make_path(const char *dir, const char *name) {
    char *p = path_buf;
    while (*dir) *p++ = *dir++;
    if (p > path_buf && *(p - 1) != '/') *p++ = '/';
    while (*name) *p++ = *name++;
    *p = '\0';
}

/* Read 2-byte big-endian word */
unsigned int read_word(unsigned char *buf) {
    return ((unsigned int)buf[0] << 8) | (unsigned int)buf[1];
}

/* Write 2-byte big-endian word */
void write_word(unsigned char *buf, unsigned int val) {
    buf[0] = (unsigned char)(val >> 8);
    buf[1] = (unsigned char)(val & 0xFF);
}

int main(int argc, char **argv) {
    const char *mod_dir = "/dd/MODS";
    const char *out_img = "/dd/deep65280.new.img";
    int out_fd;
    int in_fd;
    int i;
    int actual;
    unsigned int g;
    unsigned int total_size;
    unsigned int curr_addr;
    unsigned int krn_exec_offset;
    unsigned int mod_sizes[16];
    int num_mods;
    errnum err;

    if (argc > 1) mod_dir = argv[1];
    if (argc > 2) out_img = argv[2];

    printf("Building deep65280 boot image: %s\n", out_img);
    printf("Source modules directory: %s\n", mod_dir);

    /* 1. Create output file (mode 2 = write, attrs = 3 = read/write) */
    err = Os9Create(out_img, 3, 3, &out_fd);
    if (err == 218) { /* File exists */
        Os9Delete(out_img);
        err = Os9Create(out_img, 3, 3, &out_fd);
    }
    if (err) {
        printf("Error %u: cannot create %s\n", err, out_img);
        return 1;
    }

    /* 2. Zero-fill 64KB */
    printf("Zeroing 64KB image...\n");
    memset(io_buf, 0, sizeof(io_buf));
    for (i = 0; i < 128; i++) { /* 128 * 512 = 65536 */
        err = Os9Write(out_fd, io_buf, sizeof(io_buf), &actual);
        if (err || actual != sizeof(io_buf)) {
            printf("Error writing zero buffer: %u\n", err);
            Os9Close(out_fd);
            return 1;
        }
    }

    /* 3. Pack module slot groups */
    for (g = 0; slot_groups[g].mods != NULL; g++) {
        const char **m = slot_groups[g].mods;
        total_size = 0;
        num_mods = 0;

        /* First pass: read headers and compute sizes */
        while (*m != NULL) {
            make_path(mod_dir, *m);
            err = Os9Open(path_buf, 1, &in_fd);
            if (err) {
                printf("Error %u: cannot open %s\n", err, path_buf);
                Os9Close(out_fd);
                return 1;
            }
            err = Os9Read(in_fd, io_buf, 12, &actual);
            if (err || actual != 12) {
                printf("Error reading header %s\n", path_buf);
                Os9Close(in_fd);
                Os9Close(out_fd);
                return 1;
            }
            Os9Close(in_fd);

            if ((unsigned char)io_buf[0] != 0x87 || (unsigned char)io_buf[1] != 0xCD) {
                printf("Error: invalid module sync in %s\n", path_buf);
                Os9Close(out_fd);
                return 1;
            }

            mod_sizes[num_mods] = read_word((unsigned char *)io_buf + 2);
            total_size += mod_sizes[num_mods];
            num_mods++;
            m++;
        }

        if (slot_groups[g].end_addr - total_size < slot_groups[g].start_addr) {
            printf("Error: slot overflow for slot ending at $%04X\n", slot_groups[g].end_addr);
            Os9Close(out_fd);
            return 1;
        }

        curr_addr = slot_groups[g].end_addr - total_size;

        /* Second pass: copy module data into image at calculated offset */
        m = slot_groups[g].mods;
        for (i = 0; i < num_mods; i++) {
            int bytes_left;
            make_path(mod_dir, *m);
            err = Os9Open(path_buf, 1, &in_fd);
            if (err) {
                printf("Error %u: cannot reopen %s\n", err, path_buf);
                Os9Close(out_fd);
                return 1;
            }

            printf("  Slot mod: %-12s at $%04X (size %u)\n", *m, curr_addr, mod_sizes[i]);

            /* Seek to curr_addr in output image */
            Os9Seek(out_fd, 0, curr_addr);

            bytes_left = mod_sizes[i];
            while (bytes_left > 0) {
                int to_read = (bytes_left > (int)sizeof(io_buf)) ? (int)sizeof(io_buf) : bytes_left;
                err = Os9Read(in_fd, io_buf, to_read, &actual);
                if (err || actual <= 0) break;
                Os9Write(out_fd, io_buf, actual, &actual);
                bytes_left -= actual;
            }
            Os9Close(in_fd);

            curr_addr += mod_sizes[i];
            m++;
        }
    }

    /* 4. Place Kernel (krn) at $EE00 */
    make_path(mod_dir, "krn");
    err = Os9Open(path_buf, 1, &in_fd);
    if (err) {
        printf("Error %u: cannot open %s\n", err, path_buf);
        Os9Close(out_fd);
        return 1;
    }
    err = Os9Read(in_fd, io_buf, 12, &actual);
    if (err || actual != 12) {
        printf("Error reading krn header\n");
        Os9Close(in_fd);
        Os9Close(out_fd);
        return 1;
    }
    if ((unsigned char)io_buf[0] != 0x87 || (unsigned char)io_buf[1] != 0xCD) {
        printf("Error: invalid sync in krn\n");
        Os9Close(in_fd);
        Os9Close(out_fd);
        return 1;
    }
    total_size = read_word((unsigned char *)io_buf + 2);
    krn_exec_offset = read_word((unsigned char *)io_buf + 9);
    Os9Close(in_fd);

    printf("  Kernel:   krn          at $%04X (size %u, exec $%04X)\n",
           KRN_START_ADDR, total_size, KRN_START_ADDR + krn_exec_offset);

    Os9Seek(out_fd, 0, KRN_START_ADDR);
    err = Os9Open(path_buf, 1, &in_fd);
    {
        /* Note: For krn, the file includes post-emod data (SWIStack and interrupt trampolines
         * at $FEEE..$FEFF in the $FExx page). Do not limit copying to the module header size
         * M$Size, but copy until EOF (up to $FF00 - KRN_START_ADDR = 4352 bytes).
         */
        int bytes_left = 0x1100;
        while (bytes_left > 0) {
            int to_read = (bytes_left > (int)sizeof(io_buf)) ? (int)sizeof(io_buf) : bytes_left;
            err = Os9Read(in_fd, io_buf, to_read, &actual);
            if (err || actual <= 0) break;
            Os9Write(out_fd, io_buf, actual, &actual);
            bytes_left -= actual;
        }
    }
    Os9Close(in_fd);

    /* 5. CPU Vectors at $FFF0..$FFFF */
    Os9Seek(out_fd, 0, 0xFFF0U);
    write_word((unsigned char *)io_buf, 0xFEEEU);     /* TRAP / Reserved */
    write_word((unsigned char *)io_buf + 2, 0xFEEEU); /* SWI3 */
    write_word((unsigned char *)io_buf + 4, 0xFEF1U); /* SWI2 */
    write_word((unsigned char *)io_buf + 6, 0xFEF4U); /* FIRQ */
    write_word((unsigned char *)io_buf + 8, 0xFEF7U); /* IRQ */
    write_word((unsigned char *)io_buf + 10, 0xFEFAU);/* SWI */
    write_word((unsigned char *)io_buf + 12, 0xFEFDU);/* NMI */
    write_word((unsigned char *)io_buf + 14, KRN_START_ADDR + krn_exec_offset); /* RESET */
    Os9Write(out_fd, io_buf, 16, &actual);

    printf("Vectors installed. Reset vector: $%04X\n", KRN_START_ADDR + krn_exec_offset);

    Os9Close(out_fd);
    printf("Successfully created boot image: %s\n", out_img);
    return 0;
}
