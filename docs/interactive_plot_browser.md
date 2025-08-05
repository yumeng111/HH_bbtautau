## Set up your personal interactive plot browser
[Interactive plot browser instructions from CMS Common Analysis Tools](https://cms-analysis.docs.cern.ch/guidelines/other/plot_browser/#install-the-plot-browser)

There are detialed instructions on the page above with pictures for guidance. Once you submit the form to register a personal website, you can change some configurations (enabling `Use .htaccess files` etc.).

It is important that you share the EOS user space directory with `wwweos` account as directed on the instructions webpage above. Once shared, your personal interactive plot browser will become available.

After you have your interactive plot browser ready, you can run a simple script to post your plots as follows:

```sh
python3 /eos/user/u/username/php-plots/bin/pb_deploy_plots.py /path-to-where-you-currently-have-your-plots-saved/ /eos/user/u/username/php-plots/directory-where-you-want-your-plots-posted/ --recursive --pdf-to-png
```

Note:

- The `--pdf-to-png` command is to convert your .pdf format plots to a .png copy.
- `/eos/user/u/username/` is your eos space with `/u/username` string is just a placeholder in the instructions here and should be unique to you.
- The directory `/eos/user/u/username/php-plots/` is where you cloned the Plot Browser git repository (i.e. `cms-analysis/general/php-plots`). 