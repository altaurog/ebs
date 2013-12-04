#!/usr/bin/env python
import collections
import csv
import random
import sys

from datetime import datetime, time, timedelta

import numpy as np
from matplotlib import dates, pyplot

random.seed()

class Evidence(object):
    def __init__(self, filepath):
        self.estimate = []
        self.actual = []
        self.projects = []

        # estimated time for project
        self.proj_estimate = collections.defaultdict(int)
        # total actual time of estimated tasks
        self.proj_est_actual = collections.defaultdict(int)
        # total actual time of project, including tasks
        # which were left out of estimate
        self.proj_all_actual = collections.defaultdict(int)
        # estimated times for remaining tasks
        self.proj_todo = collections.defaultdict(list)
        with open(filepath) as f:
            r = csv.reader(f)
            r.next()
            for i, row in enumerate(r):
                project, task, estimate, actual = row[:4]
                if actual:
                    actual = float(actual)
                    self.proj_all_actual[project] += actual
                if estimate:
                    estimate = float(estimate)
                    if actual:
                        self.proj_estimate[project] += estimate
                        self.proj_est_actual[project] += actual
                        self.estimate.append(estimate)
                        self.actual.append(actual)
                    else:
                        self.proj_todo[project].append(estimate)
                        if project not in self.projects:
                            self.projects.append(project)
        self.velocity = [e/a for e, a in zip(self.estimate, self.actual)]
        self.velocity.sort()

        # determine buffer factor for task left out of estimates
        self.proj_buffer = []
        for project, all_actual in self.proj_all_actual.iteritems():
            try:
                est_actual = self.proj_est_actual[project]
            except KeyError:
                pass
            else:
                if est_actual > 0:
                    self.proj_buffer.append(all_actual/est_actual)
        self.proj_buffer.sort()

    def cdf(self, velocity):
        cdfx = [1/v for v in velocity]
        cdfx.sort()
        count = len(cdfx)
        cdfy = [float(i+1)/count for i in range(count)]
        return cdfx, cdfy

    count = 1000
    def montecarlo(self, count=None):
        count = count or self.count
        runs = dict((p, []) for p in self.projects)
        for i in range(count):
            time_remaining = 0
            for project in self.projects:
                task_estimates = self.proj_todo[project]
                t = 0
                for task in task_estimates:
                    t += task / random.choice(self.velocity)
                time_remaining += t * random.choice(self.proj_buffer)
                runs[project].append(time_remaining)
        step = count / 10
        start = step - 1
        results = {}
        for project in self.projects:
            times = sorted(runs[project])
            results[project] = times[start::step]
        return results


class Schedule(object):
    def __init__(self, start, rules):
        self.rules = rules
        self.start = start

    def get_hours(self, dt):
        dt = datetime.combine(dt.date(), time(0))
        for r, hours in self.rules:
            if r.between(dt, dt, inc=True):
                return hours
        return 0

    def calendar_days(self, by_project):
        timeline = []
        results = {}
        for p, times in by_project.iteritems():
            timeline.extend([t, p] for t in times)
            results[p] = []
        timeline.sort()
        day, total = self.start, 0
        for d in timeline:
            while d[0] > total:
                day += timedelta(1)
                total += self.get_hours(day)
            results[d[1]].append(day)
        return results

    def plot(self, montecarlo, title):
        cd = self.calendar_days(montecarlo)
        y = np.linspace(10,100,10)
        lscmap = pyplot.get_cmap('copper', lut=len(montecarlo))
        for i, (p, x) in enumerate(cd.iteritems()):
            pyplot.plot(x, y, label=p, linewidth=2, color=lscmap(i));
        pyplot.legend(loc='best');
        pyplot.title(title);
        pyplot.xlabel('Completion date');
        pyplot.ylabel('Confidence');
        pyplot.grid();
        pyplot.axes().xaxis.set_major_formatter(dates.DateFormatter('%b %d'));
        pyplot.show()

def main():
    context = {}
    execfile(sys.argv[2], context)
    start = context.get('start', datetime.now())
    rules = context['rules']
    schedule = Schedule(start, rules)
    ebs = Evidence(sys.argv[1])
    title = 'Dev schedule: current projects'
    schedule.plot(ebs.montecarlo(), title)

if __name__ == '__main__':
    main()

