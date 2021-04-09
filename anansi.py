#!/usr/bin/pyton
import yaml
import reader
import logging
import logging.config
import viewer.backlog
from pandasgui import show


with open("log_config.yaml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger(__name__)
logger.info("Starting anansi. Let's do some tricsktery!")

with open("config.yml", "r") as f:
    config = yaml.load(f.read(), Loader=yaml.FullLoader)

    # Add special "issue_type" Total to ensure we can see the total in all graphs
    config["issue_type"].insert(0, "Total")

cycle_data = reader.read_data(config)
backlog = viewer.backlog.Backlog(cycle_data, config)
# backlog.draw_treemap().show()
backlog.show_all()
# backlog.draw_pbis_epic("Done").show()
# show(treemap_data,settings={'block': True})


# fig_histogram_story_points = add_percentile(treemap_data,fig_histogram_story_points)
