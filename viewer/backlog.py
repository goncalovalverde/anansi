import pandas as pd
import plotly.express as px
import numpy as np


class Backlog:
    def __init__(self, cycle_data, config):
        self.cycle_data = cycle_data
        self.config = config
        self.treemap_data = self.get_treemap_data(cycle_data)
        self.treemap_data = self.calculate_cycle_time(self.treemap_data)

    def draw_treemap(self):
        fig = px.treemap(
            self.treemap_data.query('Status=="Done"'),
            path=["Epic Name", "Type", "Composed"],
        )
        return fig

    def draw_distribution(self):
        fig = px.scatter(
            self.treemap_data,
            x=["Done", "In Progress"],
            y="Epic Name",
            title="Done and In progress dates",
        )

        return fig

    def draw_pbis_epic(self, status):
        """ Draw pbis per epic. status could be either Done or Created"""

        fig = px.histogram(
            self.treemap_data,
            x=[status],
            title=f"{status} PBI's per Epic",
            color="Epic Name",
        )
        return fig

    def draw_story_points(self):
        fig = px.histogram(
            treemap_data,
            x=["Story Points"],
            title="Story points delivered",
            color="Epic Name",
        )
        return fig

    def draw_timeline(self):
        fig = px.timeline(
            treemap_data,
            x_start="In Progress" if "In Progress" else "Created",
            x_end="Done",
            y="Summary",
            color="Epic Name",
        )
        fig.update_layout(yaxis={"visible": False})
        return fig

    def draw_type_issue(self):
        fig = px.histogram(
            self.treemap_data, x=["Type"], title="Type of issue", color="Epic Name"
        )
        return fig

    def draw_timeline_size(self):
        fig = px.scatter(
            self.treemap_data.query('Status=="Done"'),
            x=["Done"],
            y="Epic Name",
            size="Cycle Time",
            title="When things where done and how big",
        )
        return fig

    def show_all(self):
        self.draw_treemap().show()
        self.draw_distribution().show()
        self.draw_pbis_epic("Done").show()
        self.draw_pbis_epic("Created").show()
        self.draw_story_points().show()
        self.draw_timeline().show()
        self.draw_type_issue().show()
        self.draw_timeline_size().show()

    def get_treemap_data(self, df):
        non_epics = df.query('Type != "Epic"')
        epics = df.query('Type == "Epic"')
        epics = epics.rename(columns={"Key": "Epic Key", "Summary": "Epic Name"})

        merged = pd.merge(
            non_epics,
            epics[["Epic Key", "Epic Name"]],
            left_on="Epic Link",
            right_on="Epic Key",
            how="left",
        )
        merged["Epic Name"].fillna("No Epic", inplace=True)
        merged["Composed"] = merged["Key"] + "\n" + merged["Summary"]
        # Filling NaN to 1 so that we can display the story points in the treemap
        # merged['Story Points'].fillna(1,inplace=True)
        return merged

    def add_percentile(self, df, fig):
        percentile = df.quantile([0.5, 0.85, 0.95])

        for key in percentile.keys():
            position = percentile[key]
            print(key)
            # label = f"{int(key*100)}%"

            fig = fig.add_shape(
                type="line",
                yref="paper",
                x0=position,
                y0=0,
                x1=position,
                y1=0.95,
                line_dash="dash",
            )

            fig = fig.add_annotation(x=position, yref="paper", y=1, showarrow=False)
        return fig

    def calculate_cycle_time(self, treemap_data):
        treemap_data["Cycle Time"] = pd.to_numeric(
            (treemap_data["Done"] - treemap_data["In Progress"]).dt.days,
            downcast="integer",
        )
        treemap_data["Cycle Time"].fillna(0, inplace=True)
        return treemap_data