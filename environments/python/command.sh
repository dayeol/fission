perf record --stat -g -o /app/vol/perf.data python3 server.py
cd /app/vol
perf script --symfs=/host --kallsyms=/proc/kallsyms > perf.script
perf report -T --symfs=/host --kallsyms=/proc/kallsyms --stdio > perf.report
