import os
import json
from typing import Dict, Any
from datetime import datetime

from . import Publisher
from storage import ResultsData


class WebPublisher(Publisher):
    """Publisher that generates static HTML pages for web hosting"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.output_dir = config.get('output_dir', 'web')
        self.title = config.get('title', '3GS Fantasy Results')
    
    def validate_config(self) -> bool:
        return True  # Web publisher has minimal requirements
    
    def publish(self, results_data: ResultsData) -> bool:
        """Generate static HTML page with results"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Generate HTML
            html_content = self._generate_html(results_data)
            
            # Save main index.html
            index_path = os.path.join(self.output_dir, 'index.html')
            with open(index_path, 'w') as f:
                f.write(html_content)
            print(f"Web page generated: {index_path}")
            
            # Save timestamped version
            timestamp = results_data.timestamp.strftime('%Y%m%d_%H%M%S')
            week_str = f"week_{results_data.week_number}_" if results_data.week_number else ""
            timestamped_path = os.path.join(self.output_dir, f"{week_str}results_{timestamp}.html")
            with open(timestamped_path, 'w') as f:
                f.write(html_content)
            print(f"Timestamped version saved: {timestamped_path}")
            
            # Save CSV for download
            csv_path = os.path.join(self.output_dir, 'results.csv')
            with open(csv_path, 'w') as f:
                f.write(results_data.to_csv())
            
            # Save JSON for API access
            json_path = os.path.join(self.output_dir, 'results.json')
            with open(json_path, 'w') as f:
                json.dump(results_data.to_dict(), f, indent=2)
            
            # Generate results history
            self._update_history(results_data)
            
            return True
            
        except Exception as error:
            print(f"Web publisher error: {error}")
            return False
    
    def _generate_html(self, results_data: ResultsData) -> str:
        """Generate HTML page content"""
        wins_data = results_data.get_max_wins_data()
        points_data = results_data.get_max_points_data()
        
        # Generate table rows
        table_rows = ""
        for i, row in enumerate(results_data.results, 1):
            table_rows += f"""
            <tr>
                <td>{i}</td>
                <td>{row.name}</td>
                <td>{row.results[0]}</td>
                <td>{row.results[1]}</td>
                <td>{row.results[2]}</td>
            </tr>
            """
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .header {{
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .summary-card h3 {{
            color: #333;
            margin-top: 0;
        }}
        
        .highlight {{
            font-size: 1.2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .table-container {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background-color: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        tr:hover {{
            background-color: #e3f2fd;
        }}
        
        .download-links {{
            text-align: center;
            margin: 30px 0;
        }}
        
        .download-links a {{
            display: inline-block;
            margin: 0 10px;
            padding: 10px 20px;
            background-color: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        
        .download-links a:hover {{
            background-color: #5a67d8;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .summary {{
                grid-template-columns: 1fr;
            }}
            
            table {{
                font-size: 0.9em;
            }}
            
            th, td {{
                padding: 8px 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.title}</h1>
        <p>Week {results_data.week_number if results_data.week_number else 'TBD'} Results</p>
        <p>Updated: {results_data.timestamp.strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>
    
    <div class="summary">
        <div class="summary-card">
            <h3>🏆 Most Wins</h3>
            <div class="highlight">{wins_data['max_wins']} wins</div>
            <p>{wins_data['players']}</p>
        </div>
        
        <div class="summary-card">
            <h3>📊 Most Points</h3>
            <div class="highlight">{points_data['max_points']} points</div>
            <p>{points_data['players']}</p>
        </div>
    </div>
    
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Player</th>
                    <th>Points</th>
                    <th>Wins</th>
                    <th>Losses</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    
    <div class="download-links">
        <a href="results.csv" download>Download CSV</a>
        <a href="results.json" download>Download JSON</a>
        <a href="history.html">View History</a>
    </div>
    
    <div class="footer">
        <p>Generated by 3GS Automation • Last updated: {results_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
        """
    
    def _update_history(self, results_data: ResultsData):
        """Update the history page with past results"""
        history_file = os.path.join(self.output_dir, 'history.json')
        
        # Load existing history
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        # Add current results
        current_entry = {
            "timestamp": results_data.timestamp.isoformat(),
            "week_number": results_data.week_number,
            "max_wins": results_data.get_max_wins_data(),
            "max_points": results_data.get_max_points_data(),
            "results_count": len(results_data.results)
        }
        
        # Keep only the last 20 entries
        history.insert(0, current_entry)
        history = history[:20]
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Generate history HTML
        self._generate_history_html(history)
    
    def _generate_history_html(self, history):
        """Generate HTML page showing results history"""
        history_rows = ""
        for entry in history:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            history_rows += f"""
            <tr>
                <td>{entry.get('week_number', 'N/A')}</td>
                <td>{timestamp.strftime('%Y-%m-%d %H:%M')}</td>
                <td>{entry['max_wins']['max_wins']}</td>
                <td>{entry['max_wins']['players']}</td>
                <td>{entry['max_points']['max_points']}</td>
                <td>{entry['max_points']['players']}</td>
                <td>{entry['results_count']}</td>
            </tr>
            """
        
        history_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - History</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }}
        .header {{ text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .table-container {{ background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background-color: #667eea; color: white; padding: 15px; text-align: left; }}
        td {{ padding: 12px 15px; border-bottom: 1px solid #eee; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        tr:hover {{ background-color: #e3f2fd; }}
        .back-link {{ text-align: center; margin: 20px 0; }}
        .back-link a {{ display: inline-block; padding: 10px 20px; background-color: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.title} - History</h1>
        <p>Past Results Overview</p>
    </div>
    
    <div class="back-link">
        <a href="index.html">← Back to Current Results</a>
    </div>
    
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Week</th>
                    <th>Date</th>
                    <th>Top Wins</th>
                    <th>Win Leaders</th>
                    <th>Top Points</th>
                    <th>Point Leaders</th>
                    <th>Players</th>
                </tr>
            </thead>
            <tbody>
                {history_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        history_path = os.path.join(self.output_dir, 'history.html')
        with open(history_path, 'w') as f:
            f.write(history_html)