import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SequenceDisplay from './SequenceDisplay';

function Workspace({ sequence, onSequenceUpdate }) {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStep, setEditingStep] = useState(null);
  const [parsedSequence, setParsedSequence] = useState(null);
  const [newStep, setNewStep] = useState({
    type: 'email',
    content: '',
    delay: 0,
    personalization_tips: '',
  });

  console.log('Workspace received sequence:', sequence);

  useEffect(() => {
    console.log('Workspace useEffect - sequence changed:', sequence);
    // Parse the sequence if it's a string
    if (typeof sequence === 'string') {
      try {
        console.log('Parsing string sequence');
        const parsed = JSON.parse(sequence);
        console.log('Parsed sequence:', parsed);
        
        // Handle the nested structure
        if (parsed.tool_result) {
          console.log('Found tool_result, parsing:', parsed.tool_result);
          const toolResult = JSON.parse(parsed.tool_result);
          setParsedSequence(toolResult);
        } else if (parsed.metadata && parsed.steps) {
          console.log('Found direct sequence data');
          setParsedSequence(parsed);
        } else {
          console.error('Invalid sequence data structure:', parsed);
        }
      } catch (e) {
        console.error('Error parsing sequence:', e, 'Raw sequence:', sequence);
      }
    } else if (sequence && typeof sequence === 'object') {
      console.log('Using object sequence directly:', sequence);
      setParsedSequence(sequence);
    } else {
      console.log('No sequence data received');
    }
  }, [sequence]);

  const handleOpenDialog = (step) => {
    if (step) {
      setEditingStep(step);
      setNewStep(step);
    } else {
      setEditingStep(null);
      setNewStep({
        type: 'email',
        content: '',
        delay: 0,
        personalization_tips: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingStep(null);
    setNewStep({
      type: 'email',
      content: '',
      delay: 0,
      personalization_tips: '',
    });
  };

  const handleSaveStep = () => {
    if (!newStep.content) return;

    let updatedSteps;
    if (editingStep) {
      updatedSteps = parsedSequence.steps.map((step) =>
        step.id === editingStep.id ? { ...newStep, id: step.id } : step
      );
    } else {
      updatedSteps = [...(parsedSequence?.steps || []), { ...newStep, id: Date.now().toString() }];
    }

    // Call the parent's onSequenceUpdate with the updated steps
    if (typeof onSequenceUpdate === 'function') {
      try {
        onSequenceUpdate(updatedSteps);
        console.log('Sequence updated with new steps:', updatedSteps);
      } catch (error) {
        console.error('Error updating sequence:', error);
      }
    } else {
      console.warn('onSequenceUpdate is not provided or not a function');
    }

    handleCloseDialog();
  };

  const handleStepUpdate = (updatedSteps) => {
    console.log('Workspace received step update:', updatedSteps);
    
    // Call the parent's onSequenceUpdate with the updated steps
    if (typeof onSequenceUpdate === 'function') {
      try {
        onSequenceUpdate(updatedSteps);
        console.log('Sequence updated through SequenceDisplay');
      } catch (error) {
        console.error('Error updating sequence from SequenceDisplay:', error);
      }
    } else {
      console.warn('onSequenceUpdate is not provided or not a function');
    }
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3, overflow: 'auto' }}>
      <Paper sx={{ height: '100%', p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h5">Recruiting Sequence</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Step
          </Button>
        </Box>

        {parsedSequence && (
          <SequenceDisplay sequence={parsedSequence} onStepUpdate={handleStepUpdate} />
        )}
      </Paper>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingStep ? 'Edit Step' : 'Add New Step'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              select
              label="Type"
              value={newStep.type}
              onChange={(e) => setNewStep({ ...newStep, type: e.target.value })}
              fullWidth
            >
              <MenuItem value="email">Email</MenuItem>
              <MenuItem value="linkedin">LinkedIn Message</MenuItem>
              <MenuItem value="call">Phone Call</MenuItem>
              <MenuItem value="meeting">Meeting</MenuItem>
            </TextField>
            <TextField
              label="Content"
              multiline
              rows={4}
              value={newStep.content}
              onChange={(e) => setNewStep({ ...newStep, content: e.target.value })}
              fullWidth
            />
            <TextField
              label="Delay (days)"
              type="number"
              value={newStep.delay}
              onChange={(e) =>
                setNewStep({ ...newStep, delay: parseInt(e.target.value) || 0 })
              }
              fullWidth
            />
            <TextField
              label="Personalization Tips"
              multiline
              rows={2}
              value={newStep.personalization_tips}
              onChange={(e) =>
                setNewStep({ ...newStep, personalization_tips: e.target.value })
              }
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveStep} variant="contained" color="primary">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Workspace; 