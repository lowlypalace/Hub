from typing import Any, Callable, Optional, Sequence, Union, Type
from hub.core.dataset import Dataset


def clean_labels(
    dataset: Type[Dataset],
    dataset_valid: Optional[Type[Dataset]] = None,
    transform: Optional[Callable] = None,
    tensors: Optional[Sequence[str]] = None,
    batch_size: int = 64,
    module: Union[Any, Callable, None] = None,
    criterion: Optional[Any] = None,
    optimizer: Optional[Any] = None,
    optimizer_lr: int = 0.01,
    device: Union[str, Any, None] = None,
    epochs: int = 10,
    shuffle: bool = False,
    folds: int = 5,
    create_tensors: bool = False,
    overwrite: bool = False,
    verbose: bool = True,
):
    """
    Finds label errors in a dataset with cleanlab (github.com/cleanlab) open-source library.

    Note:
        Currently, only image classification tasks is supported. Therefore, the method accepts two tensors for the images and labels (e.g. `['images', 'labels']`).
        The tensors can be specified in `transofrm` or `tensors`. Any PyTorch module can be used as a classifier.

    Args:
        dataset (class): Hub Dataset for training. The label issues will be computed for training set.
        dataset_valid (class, Optional): Hub Dataset to use as a validation set for training. The label issues will not be computed for this set. Default is `None`.
        transform (Callable, Optional): Transformation function to be applied to each sample. Default is `None`.
        tensors (list, Optional): A list of two tensors (in the images, labels order) that would be considered for finding label issues (e.g. `['images', 'labels']`).
        batch_size (int): Number of samples per batch to load. If `batch_size` is -1, a single batch with all the data will be used during training and validation. Default is `64`.
        module (class): A PyTorch torch.nn.Module module (class or instance). Default is `torchvision.models.resnet18()`.
        criterion (class): An uninitialized PyTorch criterion (loss) used to optimize the module. Default is `torch.nn.CrossEntropyLoss`.
        optimizer (class): An uninitialized PyTorch optimizer used to optimize the module. Default is `torch.optim.SGD`.
        optimizer_lr (int): The learning rate passed to the optimizer. Default is 0.01.
        device (str, torch.device): The compute device to be used. Default is `'cuda:0'` if available, else `'cpu'`.
        fold (int): Sets the number of cross-validation folds used to compute out-of-sample probabilities for each example in the dataset. The default is 5.
        epochs (int): The number of epochs to train for each `fit()` call. Note that you may keyboard-interrupt training at any time. Default is 10.
        shuffle (bool): Whether to shuffle the data before each epoch. Default is `False`.
        create_tensors (bool): if True, will create tensors `is_label_issue` and `label_quality_scores` under `label_issues group`. This would only work if you have write access to the dataset. Default is False.
        overwrite (bool): If True, will overwrite label_issues tensors if they already exists. Only applicable if `create_tensors` is True. Default is False.
        verbose (bool): This parameter controls how much output is printed. Default is True.

    Returns:
        label_issues: A boolean mask for the entire dataset where True represents a label issue and False represents an example that is confidently/accurately labeled.
        label_quality_scores: Returns label quality scores for each datapoint, where lower scores indicate labels less likely to be correct.

    Raises:
        ...

    """

    from hub.integrations.cleanlab import get_label_issues
    from hub.integrations.cleanlab import create_label_issues_tensors
    from hub.integrations.cleanlab.utils import is_dataset

    # Catch most common user errors early.
    if not is_dataset(dataset):
        raise TypeError(f"`dataset` must be a Hub Dataset. Got {type(dataset)}")

    if dataset_valid and not is_dataset(dataset_valid):
        raise TypeError(
            f"`dataset_valid` must be a Hub Dataset. Got {type(dataset_valid)}"
        )

    if create_tensors and dataset.read_only:
        raise ValueError(
            f"`create_tensors` is True but dataset is read-only. Try loading the dataset with `read_only=False.`"
        )

    label_issues, label_quality_scores, guessed_labels = get_label_issues(
        dataset=dataset,
        dataset_valid=dataset_valid,
        transform=transform,
        tensors=tensors,
        batch_size=batch_size,
        module=module,
        criterion=criterion,
        optimizer=optimizer,
        optimizer_lr=optimizer_lr,
        device=device,
        epochs=epochs,
        shuffle=shuffle,
        folds=folds,
        verbose=verbose,
    )

    if create_tensors:
        create_label_issues_tensors(
            dataset=dataset,
            label_issues=label_issues,
            label_quality_scores=label_quality_scores,
            guessed_labels=guessed_labels,
            overwrite=overwrite,
            verbose=verbose,
        )

    return label_issues, label_quality_scores, guessed_labels
