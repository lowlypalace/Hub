from cleanlab.filter import find_label_issues
from cleanlab.rank import get_label_quality_scores

from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score
from sklearn.base import clone

import numpy as np


def estimate_cv_predicted_probabilities(
    dataset, labels, model, folds, num_classes, verbose
):
    """
    This function computes an out-of-sample predicted
    probability for every example in a dataset using cross
    validation. Output is an `np.array` of shape (N, K) where N is
    the number of training examples and K is the number of classes.
    """

    # Initialize pred_probs array
    pred_probs = np.zeros(shape=(len(dataset), num_classes))

    # Create cross-validation object for out-of-sample predicted probabilities.
    kfold = StratifiedKFold(n_splits=folds, shuffle=True)

    if verbose:
        print(
            "Computing out-of-sample predicted probabilities with "
            f"{folds}-fold cross validation..."
        )

    # Loop through each fold and compute out-of-sample predicted probabilities.
    for fold, (train_idx, holdout_idx) in enumerate(kfold.split(X=dataset, y=labels)):

        if verbose:
            print(f"Fold {fold + 1} of {folds}...")

        # Initialize a fresh untrained model.
        model_copy = clone(model)

        # Select the training and holdout cross-validated sets.
        ds_train, ds_holdout = (
            dataset[train_idx.tolist()],
            dataset[holdout_idx.tolist()],
        )
        # Fit model to training set, predict on holdout set, and update pred_probs.
        model_copy.fit(X=ds_train)

        pred_probs_cross_val = model_copy.predict_proba(X=ds_holdout)
        pred_probs[holdout_idx] = pred_probs_cross_val

    if verbose:
        predicted_labels = pred_probs.argmax(axis=1)
        acc = accuracy_score(y_true=labels, y_pred=predicted_labels)
        print(f"Cross-validated estimate of accuracy on held-out data: {acc}")

    return pred_probs


def get_predicted_labels(dataset, label_issues, model, verbose):
    """
    This function returns the predicted labels for a dataset
    after pruning samples with label errors and training classifier
    on a cleaned dataset.
    """
    from hub.integrations.cleanlab.utils import subset_dataset

    if verbose:
        print(f"Pruning {np.sum(label_issues)} examples with label issues ...")

    label_issues_mask = ~label_issues
    cleaned_dataset = subset_dataset(dataset, label_issues_mask)

    if verbose:
        print(f"Remaining clean data has {len(cleaned_dataset)} examples.")

    # Initialize a fresh untrained model.
    model_copy = clone(model)

    if verbose:
        print("Fitting final model on the clean data...")

    # Fit model to the cleaned training set.
    model_copy.fit(X=cleaned_dataset)

    # Get a vector of predicted probabilities for each example in the original dataset.
    pred_probs = model_copy.predict_proba(X=dataset)

    # Get predicted class for each example.
    predicted_labels = pred_probs.argmax(axis=1)

    return predicted_labels


def get_label_issues(
    dataset,
    model,
    folds,
    verbose,
    label_issues_kwargs,
    label_quality_kwargs,
):
    """
    This function finds label issues of a dataset. First, it runs cross-validation to get out-of-sample
    predicted probabilities for each example. Then, it calls `filter.find_label_issues` to find label issues
    and `rank.get_label_quality_scores` to find label quality scores for each sample in the dataset.
    Finally, it fits the model on a cleaned dataset to compute predicted labels.
    """
    from hub.integrations.common.utils import get_labels, get_num_classes

    # Get tensor names from the instantiated skorch model.
    images_tensor, labels_tensor = model.images_tensor, model.labels_tensor

    # Get labels of a dataset
    labels = get_labels(dataset=dataset, labels_tensor=labels_tensor)

    # Get the number of unique classes.
    num_classes = get_num_classes(labels)

    # Compute out-of-sample predicted probabilities.
    pred_probs = estimate_cv_predicted_probabilities(
        dataset=dataset,
        labels=labels,
        model=model,
        folds=folds,
        num_classes=num_classes,
        verbose=verbose,
    )

    if verbose:
        print("Using predicted probabilities to identify label issues ...")

    label_issues = find_label_issues(
        labels=labels, pred_probs=pred_probs, **label_issues_kwargs
    )

    label_quality_scores = get_label_quality_scores(
        labels=labels, pred_probs=pred_probs, **label_quality_kwargs
    )

    if verbose:
        print(f"Identified {np.sum(label_issues)} examples with label issues.")

    predicted_labels = get_predicted_labels(
        dataset=dataset, label_issues=label_issues, model=model, verbose=verbose
    )

    return label_issues, label_quality_scores, predicted_labels
