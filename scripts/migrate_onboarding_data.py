# scripts/migrate_onboarding_data.py
import asyncio
from sqlalchemy import select
from app.core.database import aget_db, session_manager
from app.models.startups import Startup
from app.models.axiuser import AxiUser
from app.constants.constants import StartupStage
from datetime import datetime

async def migrate_preferences_to_proper_fields(dry_run=True):
    """Migrate data from preferences JSON to proper fields
    
    Args:
        dry_run: If True, only shows what would be changed without committing
    """
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made to the database")
        print("=" * 60)

    await session_manager.init()
    
    async for db in aget_db():
        try:
            result = await db.execute(
                select(AxiUser).where(
                    AxiUser.preferences.isnot(None)
                )
            )
            
            users = result.scalars().all()
            
            # Filter in Python to ensure preferences actually contain data
            users = [u for u in users if u.preferences and isinstance(u.preferences, dict) and len(u.preferences) > 0]
            
            
            migrated_count = 0
            startups_created = 0
            fields_updated = 0
            
            print(f"Found {len(users)} users with preferences data")
            print("-" * 60)
            
            for user in users:

                print("Preferences for user", user.preferences)
                if not user.preferences:
                    continue
                
                prefs = user.preferences
                print("Preferences for user", prefs)
                updated = False
                user_changes = []
                
                # Migrate advisor data
                if 'advisor_expertise' in prefs and not user.advisor_expertise:
                    user.advisor_expertise = prefs['advisor_expertise']
                    user_changes.append(f"advisor_expertise: {prefs['advisor_expertise'][:50]}...")
                    updated = True
                    fields_updated += 1
                
                # Migrate mentor data
                if 'mentoring_focus' in prefs and not user.mentoring_focus:
                    user.mentoring_focus = prefs['mentoring_focus']
                    user_changes.append(f"mentoring_focus: {prefs['mentoring_focus'][:50]}...")
                    updated = True
                    fields_updated += 1
                
                # Migrate co-founder data
                if 'cofounder_role' in prefs and not user.cofounder_role:
                    user.cofounder_role = prefs['cofounder_role']
                    user_changes.append(f"cofounder_role: {prefs['cofounder_role']}")
                    updated = True
                    fields_updated += 1
                
                if 'cofounder_skills' in prefs and not user.cofounder_skills:
                    user.cofounder_skills = prefs['cofounder_skills']
                    user_changes.append(f"cofounder_skills: {prefs['cofounder_skills'][:50]}...")
                    updated = True
                    fields_updated += 1
                
                if 'seeking_startup_stage' in prefs and not user.seeking_startup_stage:
                    user.seeking_startup_stage = prefs['seeking_startup_stage']
                    user_changes.append(f"seeking_startup_stage: {prefs['seeking_startup_stage']}")
                    updated = True
                    fields_updated += 1
                
                # Migrate partner data
                if 'organization_type' in prefs and not user.organization_type:
                    user.organization_type = prefs['organization_type']
                    user_changes.append(f"organization_type: {prefs['organization_type']}")
                    updated = True
                    fields_updated += 1
                
                if 'organization_name' in prefs and not user.organization_name:
                    user.organization_name = prefs['organization_name']
                    user_changes.append(f"organization_name: {prefs['organization_name']}")
                    updated = True
                    fields_updated += 1
                
                if 'partner_goals' in prefs and not user.partner_goals:
                    user.partner_goals = prefs['partner_goals']
                    user_changes.append(f"partner_goals: {prefs['partner_goals'][:50]}...")
                    updated = True
                    fields_updated += 1
                
                # Create startup for FOUNDERS only (not co-founders)
                if user.role.value == 'founder':
                    if 'startup_stage' in prefs or 'startup_idea' in prefs:
                        # Check if startup already exists
                        startup_result = await db.execute(
                            select(Startup).where(Startup.founder_id == user.id)
                        )
                        existing_startup = startup_result.scalar_one_or_none()
                        
                        if not existing_startup:
                            startup_stage = prefs.get('startup_stage', 'idea')
                            startup_idea = prefs.get('startup_idea', '')
                            startup_name = prefs.get('startup_name', f"{user.first_name}'s Startup")
                            target_market = prefs.get('target_market', '')
                            
                            # Validate startup_stage is valid enum value
                            try:
                                stage_enum = StartupStage(startup_stage)
                            except ValueError:
                                print(f"⚠️  Invalid startup_stage '{startup_stage}' for user {user.id}, defaulting to 'idea'")
                                stage_enum = StartupStage.IDEA
                            
                            new_startup = Startup(
                                founder_id=user.id,
                                name=startup_name,
                                description=startup_idea,
                                target_market=target_market,
                                stage=stage_enum,
                                is_active=True,
                                is_public=True,
                                team_size=1,
                                is_hiring=True,
                                founded_date=user.onboarded_at or datetime.utcnow()
                            )
                            db.add(new_startup)
                            startups_created += 1
                            user_changes.append(f"Created startup: {startup_name}")
                            updated = True
                        else:
                            user_changes.append("Startup already exists (skipped)")
                
                if updated:
                    migrated_count += 1
                    print(f"✓ User {user.id} ({user.email}) - {user.role.value}")
                    for change in user_changes:
                        print(f"  → {change}")
                    print()
            
            if dry_run:
                await db.rollback()  # Don't commit in dry run mode
            else:
                await db.commit()
            
            print("=" * 60)
            if dry_run:
                print("🔍 DRY RUN COMPLETE - No changes were made")
                print("Run with dry_run=False to apply these changes")
            else:
                print(f"✓ Migration complete!")
            print(f"  - Total users processed: {len(users)}")
            print(f"  - Users updated: {migrated_count}")
            print(f"  - Fields migrated: {fields_updated}")
            print(f"  - Startups created: {startups_created}")
            
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            import traceback
            traceback.print_exc()
            await db.rollback()
        finally:
            break  # Exit the async generator loop

if __name__ == "__main__":
    print("Starting migration of onboarding data from preferences...")
    print("=" * 60)
    
    # First run in dry_run mode to see what would change
    print("Step 1: Running in DRY RUN mode first...")
    asyncio.run(migrate_preferences_to_proper_fields(dry_run=True))
    
    # Ask for confirmation
    print("\n" + "=" * 60)
    response = input("\nDo you want to apply these changes? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print("\nStep 2: Applying changes...")
        asyncio.run(migrate_preferences_to_proper_fields(dry_run=False))
    else:
        print("\n❌ Migration cancelled. No changes were made.")