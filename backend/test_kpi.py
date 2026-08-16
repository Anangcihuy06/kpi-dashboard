import requests
from database import SessionLocal
from models import Sprint, User, Division, KPIRule, KPIRuleMetric, RawMetricsData, SprintKPIScore
from sync_service import sync_attendance_for_sprint, sync_user_metrics
from engine import DynamicKPIEngine

def test_active_sprint_sync():
    db = SessionLocal()
    
    # Get the active sprint
    active_sprint = db.query(Sprint).filter(Sprint.status == 'ACTIVE').first()
    
    if active_sprint:
        print(f'Active Sprint: {active_sprint.sprint_name} (Jira ID: {active_sprint.jira_sprint_id})')
        print(f'ID: {active_sprint.id}')
        print(f'Dates: {active_sprint.start_date} to {active_sprint.end_date}')
        
        # Get users for KPI calculation
        users = db.query(User).all()
        print(f'\nFound {len(users)} user(s) for KPI calculation:')
        
        for user in users:
            print(f'  - {user.full_name} ({user.id})')
        
        # Test attendance sync
        print('\nTesting attendance sync...')
        attendance_results = sync_attendance_for_sprint(db, active_sprint, users)
        
        print('Attendance results:')
        for user_id, att_data in attendance_results.items():
            user = db.query(User).filter(User.id == user_id).first()
            print(f'  {user.full_name}: {att_data.get("attendance_days")}/{att_data.get("target_days")} days, Late: {att_data.get("late_count")} ({att_data.get("late_percentage")}%)')
        
        # Test KPI calculation for one user
        print('\nTesting KPI calculation for first user...')
        
        # Get KPI rule
        rule = db.query(KPIRule).filter(KPIRule.is_active == True).first()
        if rule:
            print(f'Using KPI Rule: {rule.name}')
            
            metrics_defs = db.query(KPIRuleMetric).filter(KPIRuleMetric.kpi_rule_id == rule.id).all()
            rule_metrics_list = [
                {
                    "metric_key": m.metric_key,
                    "weight": float(m.weight),
                    "formula_expression": m.formula_expression,
                    "variables": m.variables,
                    "cap_score": float(m.cap_score)
                } for m in metrics_defs
            ]
            
            print(f'Rule has {len(rule_metrics_list)} metrics:')
            for metric in rule_metrics_list:
                print(f'  - {metric["metric_key"]}: weight={metric["weight"]}')
            
            # Calculate for one user
            if users:
                user = users[0]
                user_att_data = attendance_results.get(user.id, None)
                
                print(f'\nCalculating KPI for {user.full_name}...')
                
                # Use mock metrics for testing
                mock_metrics = {
                    "jira_sp": 15.0,
                    "gitlab_mr_merged": 4.0,
                    "attendance_days": float(user_att_data.get("attendance_days", 8.0)),
                    "target_days": float(user_att_data.get("target_days", 10.0)),
                    "late_count": float(user_att_data.get("late_count", 1.0)),
                    "late_percentage": float(user_att_data.get("late_percentage", 12.5)),
                    "normal_percentage": float(user_att_data.get("normal_percentage", 87.5))
                }
                
                print(f'Mock metrics: {mock_metrics}')
                
                result = DynamicKPIEngine.calculate_sprint_score(rule_metrics_list, mock_metrics)
                
                print(f'\nKPI Calculation Result:')
                print(f'Final Score: {result["final_sprint_score"]}')
                print(f'Breakdown:')
                for item in result["breakdown"]:
                    print(f'  - {item["metric_key"]}: raw={item["raw_score"]:.2f}, capped={item["capped_score"]:.2f}, weighted={item["weighted_score"]:.2f}')
        else:
            print('No active KPI rule found')
    else:
        print('No active sprint found')
    
    db.close()

if __name__ == '__main__':
    test_active_sprint_sync()