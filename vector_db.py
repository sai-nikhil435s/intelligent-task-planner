import chromadb
from chromadb.utils import embedding_functions
import uuid
import json
from typing import List, Dict, Any
from datetime import datetime

class VectorMemory:
    def __init__(self, db_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path="/tmp/chroma_db")
        # Using default embedding function (sentence-transformers)
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="task_memory",
            embedding_function=self.ef
        )

    def add_task(self, user_id: str, task_input: str, decomposition: Dict[str, Any]):
        """Stores a task and its decomposition in the vector database."""
        doc_id = str(uuid.uuid4())
        
        # Prepare metadata with new decomposition format
        metadata = {
            "user_id": user_id,
            "task_input": task_input,
            "user_request": decomposition.get("user_request", task_input),
            "timestamp": datetime.now().isoformat(),
            "subtask_count": len(decomposition.get("subtasks", [])),
            "format_version": "v2"  # Track format version for compatibility
        }
        
        # Store full decomposition as JSON
        metadata["decomposition"] = json.dumps(decomposition)
        
        # Use both task input and user request for better search
        document_text = f"{task_input}\n{decomposition.get('user_request', '')}"
        
        self.collection.add(
            ids=[doc_id],
            documents=[document_text],
            metadatas=[metadata]
        )
        
        return doc_id

    def search_similar_tasks(self, user_id: str, query: str, n_results: int = 3) -> str:
        """Retrieves similar past tasks for a specific user to provide context."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"user_id": user_id}
        )
        
        if not results['documents'] or not results['documents'][0]:
            return ""
        
        context_parts = []
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            try:
                decomp = json.loads(meta.get("decomposition", "{}"))
                user_req = decomp.get("user_request", meta.get("task_input", "Unknown task"))
                subtask_count = len(decomp.get("subtasks", []))
                
                context_parts.append(
                    f"Past Task: {user_req}\n"
                    f"Subtasks Generated: {subtask_count}\n"
                    f"Date: {meta.get('timestamp', 'Unknown')}"
                )
            except json.JSONDecodeError:
                # Fallback for old format
                context_parts.append(f"Past Task: {meta.get('goal', meta.get('task_input', 'Unknown'))}")
            
        return "\n---\n".join(context_parts)

    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves task history for a specific user."""
        results = self.collection.get(
            where={"user_id": user_id},
            limit=limit
        )
        
        history = []
        for i in range(len(results['ids'])):
            try:
                metadata = results['metadatas'][i]
                task_input = metadata.get("task_input", "")
                timestamp = metadata.get("timestamp", "")
                
                # Format timestamp for display
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        formatted_time = timestamp
                else:
                    formatted_time = "Unknown date"
                
                # Get user request
                decomp_json = metadata.get("decomposition")
                user_request = task_input  # Default to task_input
                subtask_count = 0
                
                if decomp_json:
                    try:
                        decomp = json.loads(decomp_json)
                        user_request = decomp.get("user_request", task_input)
                        subtask_count = len(decomp.get("subtasks", []))
                    except json.JSONDecodeError:
                        pass
                
                task_data = {
                    "id": results['ids'][i],
                    "task_input": task_input,
                    "user_request": user_request,
                    "display_text": f"{user_request[:50]}..." if len(user_request) > 50 else user_request,
                    "timestamp": timestamp,
                    "formatted_time": formatted_time,
                    "subtask_count": subtask_count
                }
                
                history.append(task_data)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"Error loading task history: {e}")
                continue
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return history

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Gets detailed statistics for a user's stored tasks."""
        results = self.collection.get(
            where={"user_id": user_id}
        )
        
        count = len(results['ids'])
        total_subtasks = 0
        priority_dist = {"High": 0, "Medium": 0, "Low": 0}
        
        # Calculate advanced statistics
        for metadata in results['metadatas']:
            try:
                decomp = json.loads(metadata.get("decomposition", "{}"))
                subtasks = decomp.get("subtasks", [])
                total_subtasks += len(subtasks)
                
                # Count priorities
                for subtask in subtasks:
                    priority = subtask.get("priority", "")
                    if priority in priority_dist:
                        priority_dist[priority] += 1
            except (json.JSONDecodeError, KeyError):
                continue
        
        avg_subtasks = total_subtasks / count if count > 0 else 0
        
        return {
            "total_tasks": count,
            "total_subtasks": total_subtasks,
            "avg_subtasks_per_task": round(avg_subtasks, 1),
            "priority_distribution": priority_dist,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_task_by_id(self, task_id: str) -> Dict[str, Any]:
        """Retrieves a specific task by its ID."""
        results = self.collection.get(
            ids=[task_id]
        )
        
        if not results['ids']:
            return {}
        
        metadata = results['metadatas'][0]
        try:
            decomp = json.loads(metadata.get("decomposition", "{}"))
            return {
                "id": results['ids'][0],
                "task_input": metadata.get("task_input", ""),
                "user_request": metadata.get("user_request", ""),
                "timestamp": metadata.get("timestamp", ""),
                "result": decomp
            }
        except json.JSONDecodeError:
            return {
                "id": results['ids'][0],
                "task_input": metadata.get("task_input", ""),
                "timestamp": metadata.get("timestamp", ""),
                "result": {}
            }

    def delete_task(self, user_id: str, task_id: str) -> bool:
        """Deletes a specific task."""
        try:
            # Verify the task belongs to the user
            task = self.get_task_by_id(task_id)
            if task.get("user_request"):
                # Check if we can verify ownership through metadata
                results = self.collection.get(ids=[task_id])
                if results['metadatas'] and results['metadatas'][0].get("user_id") == user_id:
                    self.collection.delete(ids=[task_id])
                    return True
            return False
        except Exception as e:
            print(f"Error deleting task: {e}")
            return False

    def migrate_old_format(self, user_id: str = None):
        """Migrate old format tasks to new format (if needed)."""
        try:
            where_clause = {"user_id": user_id} if user_id else {}
            results = self.collection.get(where=where_clause)
            
            migrated_count = 0
            for i, metadata in enumerate(results['metadatas']):
                # Check if old format (has "goal" instead of "user_request")
                if "goal" in metadata and "user_request" not in metadata:
                    try:
                        # Load old decomposition
                        old_decomp = json.loads(metadata.get("decomposition", "{}"))
                        
                        # Convert to new format
                        new_decomp = {
                            "user_request": metadata.get("goal", ""),
                            "subtasks": old_decomp.get("subtasks", [])
                        }
                        
                        # Update metadata
                        metadata["user_request"] = metadata["goal"]
                        metadata["task_input"] = metadata.get("task_input", metadata["goal"])
                        metadata["subtask_count"] = len(new_decomp.get("subtasks", []))
                        metadata["format_version"] = "v2"
                        metadata["decomposition"] = json.dumps(new_decomp)
                        
                        # Update in collection
                        self.collection.update(
                            ids=[results['ids'][i]],
                            metadatas=[metadata],
                            documents=[f"{metadata['task_input']}\n{metadata['user_request']}"]
                        )
                        
                        migrated_count += 1
                    except Exception as e:
                        print(f"Error migrating task {results['ids'][i]}: {e}")
                        continue
            
            return migrated_count
        except Exception as e:
            print(f"Migration error: {e}")
            return 0


if __name__ == "__main__":
    # Test the VectorMemory class
    memory = VectorMemory()
    
    # Test data with new format
    test_user = "user123"
    test_task = "Create a mobile app for fitness tracking"
    
    test_decomp = {
        "user_request": test_task,
        "subtasks": [
            {
                "title": "Design UI/UX",
                "priority": "High",
                "duration": "3 days",
                "explanation": "In this subtask, the user should create wireframes and mockups for the mobile app interface.",
                "resources": [
                    {"name": "Figma Design Tool", "link": "https://www.figma.com"},
                    {"name": "Material Design Guidelines", "link": "https://material.io"}
                ]
            },
            {
                "title": "Set up React Native",
                "priority": "High",
                "duration": "2 days",
                "explanation": "In this subtask, the user should initialize the React Native project and configure basic structure.",
                "resources": [
                    {"name": "React Native Docs", "link": "https://reactnative.dev"},
                    {"name": "Expo Framework", "link": "https://expo.dev"}
                ]
            }
        ]
    }
    
    # Add test task
    task_id = memory.add_task(test_user, test_task, test_decomp)
    print(f"Added task with ID: {task_id}")
    
    # Search similar tasks
    context = memory.search_similar_tasks(test_user, "build a fitness mobile app")
    print(f"Context found:\n{context}")
    
    # Get user history
    history = memory.get_user_history(test_user)
    print(f"\nUser history ({len(history)} tasks):")
    for task in history:
        print(f"- {task['task_input']} ({task['subtask_count']} subtasks)")
    
    # Get user stats
    stats = memory.get_user_stats(test_user)
    print(f"\nUser stats: {stats}")
    
    # Test migration (if old data exists)
    migrated = memory.migrate_old_format()
    print(f"\nMigrated {migrated} tasks to new format")