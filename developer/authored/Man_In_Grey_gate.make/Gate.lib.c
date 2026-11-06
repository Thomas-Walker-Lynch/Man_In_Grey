/*
  Man_In_Grey_gate·Gate - the gate of a Man_In_Grey command language.

  A gate is a program of its own, made from this module by a three-line
  *.CLI.c whose main calls Man_In_Grey_gate·Gate·run with three things fixed
  at compile time: the guard's name, the guard's path and the interpreter's
  path, the two paths relative to the gate itself. The gate invoking account can
  name neither program; who invokes a gate cannot choose what it runs.

  Setuid and owned by the interpreter account, account B, a gate runs the
  guard and the interpreter under account B while the real uid still names
  the gate invoking account, account A. Not setuid, it runs them under
  account A.

  admit reads the journal on standard input, then:

    0. settles what the invoking program handed it: opens /dev/null on any
       of descriptors 0, 1 and 2 left closed, closes every descriptor above
       2, and raises each resource limit that could stop the guard or the
       interpreter partway, refusing when one stays too low;
    1. refuses unless the guard and the interpreter, and every directory
       above them, are owned by root or by the interpreter account and
       writable by no other account;
    2. clears the environment, sets the file mode mask to 077, marks the
       process not dumpable, changes directory to /, and records the
       gate invoking account in MIG_GATE_INVOKING_UID, MIG_GATE_INVOKING_GID and
       MIG_GATE_INVOKING_NAME;
    3. starts the guard with the journal on its standard input, and admits
       the journal only when the guard exits 0 having written exactly one
       line to standard output: guard <name> check passed;
    4. starts the interpreter with the same journal.

  Every line the guard and the interpreter write is copied to the person and
  to the system log. A line that is not UTF-8, or holds a control character,
  or is too long, or one line too many, breaks the gate's rules: the gate
  stops the program and refuses.

  Exit status: 0 when the journal was admitted and executed, or admitted
  with check_only; 1 when the guard refused it or execution failed; 2 when
  the gate, guard or interpreter could not run, or broke the gate's rules.
*/

#ifndef Man_In_Grey_gate·Gate·ONCE
#define Man_In_Grey_gate·Gate·ONCE

int Man_In_Grey_gate·Gate·run(
  const char *guard_name
  ,const char *guard_relative
  ,const char *interpreter_relative
  ,int argc
  ,char **argv
);

#ifdef Man_In_Grey_gate·Gate

  #include <dirent.h>
  #include <errno.h>
  #include <fcntl.h>
  #include <libgen.h>
  #include <limits.h>
  #include <poll.h>
  #include <pwd.h>
  #include <signal.h>
  #include <stdarg.h>
  #include <stdio.h>
  #include <stdlib.h>
  #include <string.h>
  #include <sys/prctl.h>
  #include <sys/resource.h>
  #include <sys/stat.h>
  #include <sys/types.h>
  #include <sys/wait.h>
  #include <syslog.h>
  #include <unistd.h>

  #define PYTHON "/usr/bin/python3"
  #define JOURNAL_MAX ((size_t)16 << 20)
  #define OUTPUT_LINE_MAX 4096
  #define OUTPUT_LINE_COUNT_MAX 2000
  #define VERDICT_MAX 512

  Local const char *Guard_name = "";
  Local bool Logging = false;

  // ------------------------------------------------------------------------------
  // saying things: to the person on standard error, and to the system log

  Local void say(const char *tag ,const char *format ,...){
    char message[OUTPUT_LINE_MAX + 128];
    va_list ap; va_start(ap ,format);
    vsnprintf(message ,sizeof message ,format ,ap);
    va_end(ap);
    fprintf(stderr ,"gate: %s: %s\n" ,tag ,message);
    if( Logging ) syslog(LOG_NOTICE ,"%s gate: %s: %s" ,Guard_name ,tag ,message);
  }

  Local void die(const char *format ,...){
    char message[OUTPUT_LINE_MAX];
    va_list ap; va_start(ap ,format);
    vsnprintf(message ,sizeof message ,format ,ap);
    va_end(ap);
    say("cannot_run" ,"%s" ,message);
    _exit(2);
  }

  // ------------------------------------------------------------------------------
  // the ownership check

  Local bool account_changed(void){
    return geteuid() != getuid() || getegid() != getgid();
  }

  /* path and every directory above it: owned by root or by the interpreter
     account, the effective uid, and writable by no other account */
  Local void check_trusted_owner(const char *path){
    uid_t interpreter_uid = geteuid();
    char prefix[PATH_MAX];
    size_t length = strlen(path);
    if( length >= sizeof prefix ) die("path too long: %s" ,path);
    struct stat st;
    if( lstat("/" ,&st) != 0 || st.st_uid != 0 ) die("/ is not owned by root");
    for(size_t i = 1; i <= length; ++i){
      if( i < length && path[i] != '/' ) continue;
      memcpy(prefix ,path ,i); prefix[i] = '\0';
      if( lstat(prefix ,&st) != 0 ) die("cannot examine %s: %s" ,prefix ,strerror(errno));
      if( st.st_uid != 0 && st.st_uid != interpreter_uid )
        die("%s is owned by uid %ld, neither root nor the interpreter account" ,prefix ,(long)st.st_uid);
      if( st.st_mode & (S_IWGRP | S_IWOTH) )
        die("%s is writable by group or other accounts" ,prefix);
    }
  }

  // ------------------------------------------------------------------------------
  // what the invoking program hands the gate

  /* Descriptors 0, 1 and 2 open, on /dev/null when the invoking program left
     one closed, so a pipe the gate makes cannot land on one of them; every
     other descriptor closed, so nothing the invoking program opened reaches
     the guard or the interpreter. */
  Local void settle_descriptors(void){
    for(int fd = 0; fd <= 2; ++fd){
      if( fcntl(fd ,F_GETFD) >= 0 ) continue;
      int null = open("/dev/null" ,O_RDWR);
      if( null < 0 ) die("cannot open /dev/null: %s" ,strerror(errno));
      if( null != fd ){
        if( dup2(null ,fd) < 0 ) die("cannot open descriptor %d: %s" ,fd ,strerror(errno));
        close(null);
      }
    }
    DIR *dir = opendir("/proc/self/fd");
    if( !dir ) die("cannot list /proc/self/fd: %s" ,strerror(errno));
    int own = dirfd(dir);
    size_t count = 0 ,size = 64;
    int *list = malloc(size * sizeof *list);
    if( !list ) die("out of memory");
    struct dirent *entry;
    while( (entry = readdir(dir)) ){
      char *end;
      long fd = strtol(entry->d_name ,&end ,10);
      if( *end || end == entry->d_name || fd <= 2 || fd == own ) continue;
      if( count == size ){
        size *= 2;
        int *larger = realloc(list ,size * sizeof *list);
        if( !larger ) die("out of memory");
        list = larger;
      }
      list[count++] = (int)fd;
    }
    closedir(dir);
    for(size_t i = 0; i < count; ++i) close(list[i]);
    free(list);
  }

  typedef struct{
    int resource;
    const char *name;
    rlim_t need;             // RLIM_INFINITY when the limit is to be unlimited
  } Limit;

  Local void say_limit(char *text ,size_t size ,rlim_t value){
    if( value == RLIM_INFINITY ) snprintf(text ,size ,"unlimited");
    else snprintf(text ,size ,"%llu" ,(unsigned long long)value);
  }

  /* The invoking program sets the resource limits the gate starts with. A
     small file size or CPU time limit would stop the interpreter partway
     through a journal. Each limit is raised to what the gate needs, as far
     as the hard limit allows, or past it when account B is root; the gate
     refuses when a limit stays too low. */
  Local void settle_limits(void){
    const Limit limit_list[] = {
      {RLIMIT_FSIZE ,"file size (bytes)" ,RLIM_INFINITY}
      ,{RLIMIT_CPU ,"CPU time (seconds)" ,RLIM_INFINITY}
      ,{RLIMIT_AS ,"address space (bytes)" ,(rlim_t)1 << 30}
      ,{RLIMIT_DATA ,"data size (bytes)" ,(rlim_t)1 << 30}
      ,{RLIMIT_STACK ,"stack size (bytes)" ,(rlim_t)8 << 20}
      ,{RLIMIT_NOFILE ,"open files" ,64}
    };
    for(size_t i = 0; i < sizeof limit_list / sizeof limit_list[0]; ++i){
      const Limit *limit = &limit_list[i];
      struct rlimit r;
      if( getrlimit(limit->resource ,&r) != 0 ) die("cannot read the %s limit: %s" ,limit->name ,strerror(errno));
      if( r.rlim_cur >= limit->need ) continue;
      if( geteuid() == 0 && r.rlim_max < limit->need ) r.rlim_max = limit->need;
      r.rlim_cur = r.rlim_max < limit->need ? r.rlim_max : limit->need;
      setrlimit(limit->resource ,&r);
      if( getrlimit(limit->resource ,&r) != 0 ) die("cannot read the %s limit: %s" ,limit->name ,strerror(errno));
      if( r.rlim_cur < limit->need ){
        char have[32] ,want[32];
        say_limit(have ,sizeof have ,r.rlim_cur);
        say_limit(want ,sizeof want ,limit->need);
        die("the %s limit is %s; the gate needs %s" ,limit->name ,have ,want);
      }
    }
  }

  // the program at a path relative to the gate's own directory, resolved
  Local bool resolve(const char *relative ,char *resolved){
    char exe[PATH_MAX];
    ssize_t n = readlink("/proc/self/exe" ,exe ,sizeof exe - 1);
    if( n < 0 ) return false;
    exe[n] = '\0';
    char candidate[PATH_MAX];
    if( snprintf(candidate ,sizeof candidate ,"%s/%s" ,dirname(exe) ,relative) >= (int)sizeof candidate ) return false;
    return realpath(candidate ,resolved) != NULL;
  }

  // a guard name: not empty, no space, no control character
  Local bool name_is_valid(const char *name){
    if( !*name ) return false;
    for(const unsigned char *p = (const unsigned char *)name; *p; ++p)
      if( *p <= 0x20 || *p == 0x7F ) return false;
    return true;
  }

  // ------------------------------------------------------------------------------
  // the rules for what the guard and the interpreter write

  /* true when the line is UTF-8 holding no control character: none of C0,
     DEL or C1, no overlong form, no surrogate */
  Local bool line_is_clean(const unsigned char *s ,size_t n){
    size_t i = 0;
    while( i < n ){
      unsigned c = s[i];
      if( c < 0x80 ){
        if( c < 0x20 || c == 0x7F ) return false;
        ++i; continue;
      }
      unsigned code; size_t length;
      if( (c & 0xE0) == 0xC0 ){ code = c & 0x1F; length = 2; }
      else if( (c & 0xF0) == 0xE0 ){ code = c & 0x0F; length = 3; }
      else if( (c & 0xF8) == 0xF0 ){ code = c & 0x07; length = 4; }
      else return false;
      if( i + length > n ) return false;
      for(size_t k = 1; k < length; ++k){
        unsigned d = s[i + k];
        if( (d & 0xC0) != 0x80 ) return false;
        code = (code << 6) | (d & 0x3F);
      }
      if( (length == 2 && code < 0x80) || (length == 3 && code < 0x800) || (length == 4 && code < 0x10000) ) return false;
      if( code > 0x10FFFF || (code >= 0xD800 && code <= 0xDFFF) ) return false;
      if( code >= 0x80 && code <= 0x9F ) return false;
      i += length;
    }
    return true;
  }

  typedef struct{
    int fd;
    FILE *echo;              // where its lines are copied for the person
    const char *stream;      // "stdout" or "stderr", for the log
    char line[OUTPUT_LINE_MAX];
    size_t length;
  } Stream;

  typedef struct{
    const char *source;      // "guard" or "interpreter"
    bool stdout_is_verdict;  // the guard's standard output is kept, not shown
    char verdict[VERDICT_MAX];
    size_t verdict_length;
    size_t line_count;
    const char *broken;      // the rule broken, or NULL
  } Child;

  Local void finish_line(Child *child ,Stream *stream){
    if( child->broken ) return;
    if( !line_is_clean((unsigned char *)stream->line ,stream->length) ){
      child->broken = "a line that is not UTF-8 or holds a control character";
      return;
    }
    if( ++child->line_count > OUTPUT_LINE_COUNT_MAX ){
      child->broken = "more lines than the gate accepts";
      return;
    }
    stream->line[stream->length] = '\0';
    fprintf(stream->echo ,"%s: %s\n" ,child->source ,stream->line);
    fflush(stream->echo);
    syslog(LOG_NOTICE ,"%s %s: %s" ,Guard_name ,child->source ,stream->line);
    stream->length = 0;
  }

  Local void take(Child *child ,Stream *stream ,const char *bytes ,size_t n){
    for(size_t i = 0; i < n && !child->broken; ++i){
      if( bytes[i] == '\n' ){ finish_line(child ,stream); continue; }
      if( stream->length == OUTPUT_LINE_MAX - 1 ){ child->broken = "a line longer than the gate accepts"; return; }
      stream->line[stream->length++] = bytes[i];
    }
  }

  Local void take_verdict(Child *child ,const char *bytes ,size_t n){
    if( child->verdict_length + n > VERDICT_MAX - 1 ){ child->broken = "more on standard output than a verdict"; return; }
    memcpy(child->verdict + child->verdict_length ,bytes ,n);
    child->verdict_length += n;
    child->verdict[child->verdict_length] = '\0';
  }

  Local void close_on_exec(int fd){
    int flags = fcntl(fd ,F_GETFD);
    if( flags < 0 || fcntl(fd ,F_SETFD ,flags | FD_CLOEXEC) < 0 ) die("cannot set close-on-exec: %s" ,strerror(errno));
  }

  /* Start PYTHON with the arguments, give it the input on its standard input,
     and read its standard output and standard error by the gate's rules.
     Returns the wait status. */
  Local int run_child(Child *child ,char *const argument[] ,const unsigned char *input ,size_t input_length){
    int in[2] ,out[2] ,err[2];
    if( pipe(in) || pipe(out) || pipe(err) ) die("cannot make a pipe: %s" ,strerror(errno));
    for(int k = 0; k < 2; ++k){ close_on_exec(in[k]); close_on_exec(out[k]); close_on_exec(err[k]); }

    pid_t pid = fork();
    if( pid < 0 ) die("cannot start the %s: %s" ,child->source ,strerror(errno));
    if( pid == 0 ){
      if( dup2(in[0] ,0) < 0 || dup2(out[1] ,1) < 0 || dup2(err[1] ,2) < 0 ) _exit(127);
      execv(PYTHON ,argument);
      dprintf(2 ,"cannot_start: %s: %s\n" ,PYTHON ,strerror(errno));
      _exit(127);
    }
    close(in[0]); close(out[1]); close(err[1]);
    fcntl(in[1] ,F_SETFL ,fcntl(in[1] ,F_GETFL) | O_NONBLOCK);

    Stream out_stream = {.fd = out[0] ,.echo = stdout ,.stream = "stdout"};
    Stream err_stream = {.fd = err[0] ,.echo = stderr ,.stream = "stderr"};
    int in_fd = in[1];
    size_t written = 0;
    if( input_length == 0 ){ close(in_fd); in_fd = -1; }

    while( (out_stream.fd >= 0 || err_stream.fd >= 0) && !child->broken ){
      struct pollfd poll_list[3];
      int count = 0 ,in_at = -1 ,out_at = -1 ,err_at = -1;
      if( in_fd >= 0 ){ poll_list[count] = (struct pollfd){.fd = in_fd ,.events = POLLOUT}; in_at = count++; }
      if( out_stream.fd >= 0 ){ poll_list[count] = (struct pollfd){.fd = out_stream.fd ,.events = POLLIN}; out_at = count++; }
      if( err_stream.fd >= 0 ){ poll_list[count] = (struct pollfd){.fd = err_stream.fd ,.events = POLLIN}; err_at = count++; }
      if( poll(poll_list ,count ,-1) < 0 ){
        if( errno == EINTR ) continue;
        die("poll: %s" ,strerror(errno));
      }
      if( in_at >= 0 && poll_list[in_at].revents ){
        ssize_t n = write(in_fd ,input + written ,input_length - written);
        if( n > 0 ) written += (size_t)n;
        if( (n < 0 && errno != EAGAIN && errno != EINTR) || written == input_length ){ close(in_fd); in_fd = -1; }
      }
      Stream *stream_list[2] = {&out_stream ,&err_stream};
      int at_list[2] = {out_at ,err_at};
      for(int k = 0; k < 2; ++k){
        Stream *stream = stream_list[k];
        if( at_list[k] < 0 || !poll_list[at_list[k]].revents ) continue;
        char buffer[4096];
        ssize_t n = read(stream->fd ,buffer ,sizeof buffer);
        if( n < 0 && (errno == EAGAIN || errno == EINTR) ) continue;
        if( n <= 0 ){
          if( stream->length > 0 && !(stream == &out_stream && child->stdout_is_verdict) ) finish_line(child ,stream);
          close(stream->fd); stream->fd = -1;
          continue;
        }
        if( stream == &out_stream && child->stdout_is_verdict ) take_verdict(child ,buffer ,(size_t)n);
        else take(child ,stream ,buffer ,(size_t)n);
      }
    }

    if( child->broken ) kill(pid ,SIGKILL);
    if( in_fd >= 0 ) close(in_fd);
    if( out_stream.fd >= 0 ) close(out_stream.fd);
    if( err_stream.fd >= 0 ) close(err_stream.fd);
    int status = 0;
    while( waitpid(pid ,&status ,0) < 0 ){
      if( errno != EINTR ) die("waitpid: %s" ,strerror(errno));
    }
    return status;
  }

  // ------------------------------------------------------------------------------
  // the commands

  Local void print_usage(FILE *file ,const char *program){
    fprintf(file ,
      "Usage: %s <command> [option ...]\n"
      "  help | -h            print this message (also printed when given no arguments)\n"
      "  flags                print the gate invoking account, the interpreter account, the guard\n"
      "                       and the interpreter, and whether the gate changes the account\n"
      "  admit [option ...]   read a journal on standard input, run the guard, and when the\n"
      "                       guard passes the journal, run the interpreter\n"
      "Options of admit:\n"
      "  constraints <file>   given to the guard\n"
      "  check_only           run the guard and not the interpreter\n"
      ,program
    );
  }

  Local void print_flags(const char *guard_relative ,const char *interpreter_relative){
    struct passwd *pw = getpwuid(getuid());
    printf("gate_invoking.uid=%ld\n" ,(long)getuid());
    printf("gate_invoking.name=%s\n" ,pw ? pw->pw_name : "unknown");
    pw = getpwuid(geteuid());
    printf("interpreter.uid=%ld\n" ,(long)geteuid());
    printf("interpreter.name=%s\n" ,pw ? pw->pw_name : "unknown");
    printf("account_changed=%d\n" ,account_changed() ? 1 : 0);
    printf("guard.name=%s\n" ,Guard_name);
    char resolved[PATH_MAX];
    printf("guard.path=%s\n" ,resolve(guard_relative ,resolved) ? resolved : "(missing)");
    printf("interpreter.path=%s\n" ,resolve(interpreter_relative ,resolved) ? resolved : "(missing)");
  }

  Local unsigned char *read_journal(size_t *length){
    size_t size = 1 << 16;
    unsigned char *journal = malloc(size);
    if( !journal ) die("out of memory");
    *length = 0;
    for(;;){
      if( *length == size ){
        if( size >= JOURNAL_MAX ) die("the journal is larger than %zu bytes" ,(size_t)JOURNAL_MAX);
        size *= 2;
        unsigned char *larger = realloc(journal ,size);
        if( !larger ) die("out of memory");
        journal = larger;
      }
      ssize_t n = read(0 ,journal + *length ,size - *length);
      if( n < 0 ){
        if( errno == EINTR ) continue;
        die("cannot read the journal: %s" ,strerror(errno));
      }
      if( n == 0 ) break;
      *length += (size_t)n;
    }
    return journal;
  }

  int Man_In_Grey_gate·Gate·run(
    const char *guard_name
    ,const char *guard_relative
    ,const char *interpreter_relative
    ,int argc
    ,char **argv
  ){
    Guard_name = guard_name;
    const char *program = argc > 0 ? argv[0] : "gate";
    if( argc < 2 || !strcmp(argv[1] ,"help") || !strcmp(argv[1] ,"-h") || !strcmp(argv[1] ,"--help") ){
      print_usage(stdout ,program);
      return 0;
    }
    if( !strcmp(argv[1] ,"flags") && argc == 2 ){
      print_flags(guard_relative ,interpreter_relative);
      return 0;
    }
    if( strcmp(argv[1] ,"admit") ){
      fprintf(stderr ,"gate: usage: unknown command '%s'\n" ,argv[1]);
      print_usage(stderr ,program);
      return 2;
    }
    const char *constraints = NULL;
    bool check_only = false;
    for(int i = 2; i < argc; ++i){
      if( !strcmp(argv[i] ,"constraints") && i + 1 < argc ){ constraints = argv[++i]; continue; }
      if( !strcmp(argv[i] ,"check_only") ){ check_only = true; continue; }
      fprintf(stderr ,"gate: usage: unknown or incomplete option '%s'\n" ,argv[i]);
      return 2;
    }

    settle_descriptors();
    settle_limits();

    if( !name_is_valid(guard_name) ) die("the guard name compiled into this gate is empty or holds a space or control character");
    char guard_path[PATH_MAX] ,interpreter_path[PATH_MAX];
    if( !resolve(guard_relative ,guard_path) ) die("the guard is missing: %s" ,guard_relative);
    if( !resolve(interpreter_relative ,interpreter_path) ) die("the interpreter is missing: %s" ,interpreter_relative);
    check_trusted_owner(guard_path);
    check_trusted_owner(interpreter_path);

    uid_t gate_invoking_uid = getuid();
    gid_t gate_invoking_gid = getgid();
    struct passwd *pw = getpwuid(gate_invoking_uid);
    char gate_invoking_name[256];
    snprintf(gate_invoking_name ,sizeof gate_invoking_name ,"%s" ,pw ? pw->pw_name : "unknown");

    clearenv();
    setenv("PATH" ,"/usr/sbin:/usr/bin:/sbin:/bin" ,1);
    setenv("LANG" ,"C.UTF-8" ,1);
    char number[32];
    snprintf(number ,sizeof number ,"%ld" ,(long)gate_invoking_uid); setenv("MIG_GATE_INVOKING_UID" ,number ,1);
    snprintf(number ,sizeof number ,"%ld" ,(long)gate_invoking_gid); setenv("MIG_GATE_INVOKING_GID" ,number ,1);
    setenv("MIG_GATE_INVOKING_NAME" ,gate_invoking_name ,1);
    umask(077);
    prctl(PR_SET_DUMPABLE ,0 ,0 ,0 ,0);
    if( chdir("/") != 0 ) die("cannot change directory to /");
    signal(SIGPIPE ,SIG_IGN);

    openlog("Man_In_Grey_gate" ,LOG_PID ,LOG_AUTHPRIV);
    Logging = true;

    size_t journal_length;
    unsigned char *journal = read_journal(&journal_length);
    say("asked" ,"gate invoking account %s (uid %ld), journal of %zu bytes%s"
        ,gate_invoking_name ,(long)gate_invoking_uid ,journal_length ,check_only ? ", check only" : "");

    // the guard
    char *guard_argument[] = {
      (char *)PYTHON ,(char *)"-E" ,(char *)"-s" ,(char *)"-B" ,guard_path ,(char *)"check"
      ,constraints ? (char *)"constraints" : NULL ,(char *)constraints ,NULL
    };
    Child guard = {.source = "guard" ,.stdout_is_verdict = true};
    int status = run_child(&guard ,guard_argument ,journal ,journal_length);
    if( guard.broken ){
      say("refused" ,"the guard broke the gate's rules: %s" ,guard.broken);
      return 2;
    }
    char expected[VERDICT_MAX];
    snprintf(expected ,sizeof expected ,"guard %s check passed\n" ,guard_name);
    if( !WIFEXITED(status) ){
      say("refused" ,"the guard was stopped by signal %d" ,WIFSIGNALED(status) ? WTERMSIG(status) : 0);
      return 2;
    }
    if( WEXITSTATUS(status) == 1 ){
      say("refused" ,"by the guard");
      return 1;
    }
    if( WEXITSTATUS(status) != 0 ){
      say("refused" ,"the guard could not check the journal (exit status %d)" ,WEXITSTATUS(status));
      return 2;
    }
    if( strcmp(guard.verdict ,expected) ){
      say("refused" ,"the guard exited 0 without writing the one line 'guard %s check passed'" ,guard_name);
      return 2;
    }
    say("admitted" ,"guard %s check passed" ,guard_name);
    if( check_only ){
      say("not_executed" ,"check_only was asked");
      return 0;
    }

    // the interpreter
    char *interpreter_argument[] = {
      (char *)PYTHON ,(char *)"-E" ,(char *)"-s" ,(char *)"-B" ,interpreter_path ,(char *)"execute" ,NULL
    };
    Child interpreter = {.source = "interpreter" ,.stdout_is_verdict = false};
    status = run_child(&interpreter ,interpreter_argument ,journal ,journal_length);
    if( interpreter.broken ){
      say("failed" ,"the interpreter broke the gate's rules: %s; what it had done stays done" ,interpreter.broken);
      return 2;
    }
    if( !WIFEXITED(status) ){
      say("failed" ,"the interpreter was stopped by signal %d" ,WIFSIGNALED(status) ? WTERMSIG(status) : 0);
      return 2;
    }
    switch( WEXITSTATUS(status) ){
      case 0: say("executed" ,"the journal was executed"); return 0;
      case 1: say("failed" ,"execution failed"); return 1;
      default: say("failed" ,"the interpreter could not run (exit status %d)" ,WEXITSTATUS(status)); return 2;
    }
  }

#endif // Man_In_Grey_gate·Gate
#endif // Man_In_Grey_gate·Gate·ONCE
