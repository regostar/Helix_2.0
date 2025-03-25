import React, { useState, useRef, useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Stepper, 
  Step, 
  StepLabel, 
  StepContent, 
  Chip,
  IconButton,
  TextField,
  Snackbar,
  Alert
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import DeleteIcon from '@mui/icons-material/Delete';
import { useSocket } from './SocketContext';

/**
 * SequenceDisplay Component
 * @param {Object} props
 * @param {Object} props.sequence - The sequence to display
 * @param {Object} props.sequence.metadata - Metadata about the sequence
 * @param {Array} props.sequence.steps - Steps in the sequence
 * @param {Function} [props.onStepUpdate] - Optional callback when steps are updated
 */
const SequenceDisplay = ({ sequence, onStepUpdate = () => {} }) => {
  const [editableSteps, setEditableSteps] = useState({});
  const [editingStepId, setEditingStepId] = useState(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('info');
  const textFieldRef = useRef(null);
  const { socket, isConnected, emit } = useSocket();

  // Initialize editableSteps whenever sequence changes
  useEffect(() => {
    if (sequence && sequence.steps) {
      const initialEditableSteps = {};
      sequence.steps.forEach(step => {
        initialEditableSteps[step.id] = step.content;
      });
      setEditableSteps(initialEditableSteps);
      console.log('SequenceDisplay - Initialized editable steps');
    }
  }, [sequence]);

  if (!sequence || !sequence.steps) return null;

  const showSnackbar = (message, severity = 'info') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleSnackbarClose = () => {
    setSnackbarOpen(false);
  };

  const handleEditClick = (stepId, content) => {
    setEditableSteps({
      ...editableSteps,
      [stepId]: content
    });
    setEditingStepId(stepId);
    
    // Focus on the text field after a short delay
    setTimeout(() => {
      if (textFieldRef.current) {
        textFieldRef.current.focus();
      }
    }, 100);
  };

  const handleContentChange = (stepId, newContent) => {
    setEditableSteps({
      ...editableSteps,
      [stepId]: newContent
    });
  };

  const handleSaveClick = (stepId) => {
    const updatedStep = sequence.steps.find(step => step.id === stepId);
    if (!updatedStep) return;
    
    const newSteps = sequence.steps.map(step => 
      step.id === stepId 
        ? { ...step, content: editableSteps[stepId] }
        : step
    );
    
    console.log('SequenceDisplay - saving edits:', newSteps);
    console.log('onStepUpdate is:', typeof onStepUpdate);
    
    // Check if onStepUpdate is provided and is a function before calling it
    if (typeof onStepUpdate === 'function') {
      try {
        onStepUpdate(newSteps);
        console.log('onStepUpdate called successfully');
      } catch (error) {
        console.error('Error calling onStepUpdate:', error);
        showSnackbar('Error updating sequence', 'error');
      }
    } else {
      console.warn('onStepUpdate is not a function or not provided');
      showSnackbar('Could not update sequence', 'warning');
    }
    
    setEditingStepId(null);
    
    // Send to backend for processing via socket
    try {
      if (isConnected) {
        const eventData = {
          step_id: stepId,
          content: editableSteps[stepId],
          request: "Refine this step based on the edits to make it more effective"
        };
        
        const success = emit('process_edit', eventData);
        
        if (success) {
          console.log('Socket event emitted successfully');
          showSnackbar('Changes saved and being refined by AI', 'success');
        } else {
          throw new Error('Failed to emit event');
        }
      } else {
        console.warn('Socket is not connected');
        showSnackbar('Changes saved but AI refinement unavailable - socket disconnected', 'warning');
      }
    } catch (error) {
      console.error('Error emitting socket event:', error);
      showSnackbar('Error connecting to AI service', 'error');
    }
  };

  const handleCancelClick = () => {
    setEditingStepId(null);
  };

  const handleDeleteClick = (stepId) => {
    const newSteps = sequence.steps.filter(step => step.id !== stepId);
    
    console.log('SequenceDisplay - deleting step:', stepId);
    console.log('onStepUpdate is:', typeof onStepUpdate);
    
    // Check if onStepUpdate is provided and is a function before calling it
    if (typeof onStepUpdate === 'function') {
      try {
        onStepUpdate(newSteps);
        console.log('onStepUpdate called successfully for delete');
        showSnackbar('Step deleted successfully', 'success');
      } catch (error) {
        console.error('Error calling onStepUpdate for delete:', error);
        showSnackbar('Error deleting step', 'error');
      }
    } else {
      console.warn('onStepUpdate is not a function or not provided');
      showSnackbar('Could not delete step', 'warning');
    }
  };

  return (
    <Box sx={{ width: '100%', p: 2 }}>
      {/* Metadata Section */}
      <Card sx={{ mb: 3, backgroundColor: '#f5f5f5' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Sequence Details
          </Typography>
          <Typography variant="body1">
            Role: {sequence.metadata.role}
          </Typography>
          <Typography variant="body1">
            Industry: {sequence.metadata.industry}
          </Typography>
          <Typography variant="body1">
            Seniority: {sequence.metadata.seniority}
          </Typography>
          <Typography variant="body1">
            Company Type: {sequence.metadata.company_type}
          </Typography>
        </CardContent>
      </Card>

      {/* Steps Section */}
      <Stepper orientation="vertical">
        {sequence.steps.map((step, index) => (
          <Step key={step.id} active={true}>
            <StepLabel>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="subtitle1">
                  Step {index + 1}
                </Typography>
                <Chip 
                  label={step.type} 
                  color={
                    step.type === 'email' ? 'primary' :
                    step.type === 'linkedin' ? 'info' :
                    step.type === 'call' ? 'success' : 'default'
                  }
                  size="small"
                />
                <Chip 
                  label={`${step.delay} days`} 
                  variant="outlined" 
                  size="small"
                />
              </Box>
            </StepLabel>
            <StepContent>
              <Card variant="outlined" sx={{ mt: 1, mb: 2 }}>
                <CardContent sx={{ position: 'relative' }}>
                  {editingStepId === step.id ? (
                    <Box>
                      <TextField
                        inputRef={textFieldRef}
                        multiline
                        fullWidth
                        variant="outlined"
                        value={editableSteps[step.id]}
                        onChange={(e) => handleContentChange(step.id, e.target.value)}
                        sx={{ mb: 2 }}
                      />
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                        <IconButton 
                          size="small" 
                          color="primary" 
                          onClick={() => handleSaveClick(step.id)}
                          title="Save changes"
                        >
                          <SaveIcon />
                        </IconButton>
                        <IconButton 
                          size="small" 
                          onClick={handleCancelClick}
                          title="Cancel editing"
                        >
                          <CancelIcon />
                        </IconButton>
                      </Box>
                    </Box>
                  ) : (
                    <>
                      <Typography variant="body1" gutterBottom>
                        {step.content}
                      </Typography>
                      <Box sx={{ position: 'absolute', top: 8, right: 8, display: 'flex' }}>
                        <IconButton 
                          size="small"
                          onClick={() => handleEditClick(step.id, step.content)}
                          title="Edit message"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton 
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(step.id)}
                          title="Delete step"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    </>
                  )}
                  <Typography variant="subtitle2" color="textSecondary" sx={{ mt: 1 }}>
                    Personalization Tips:
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {step.personalization_tips}
                  </Typography>
                </CardContent>
              </Card>
            </StepContent>
          </Step>
        ))}
      </Stepper>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleSnackbarClose} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SequenceDisplay; 